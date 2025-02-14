import os
from typing import Optional, Iterable, Type

from django.conf import settings
from django.db import models
from haystack.exceptions import NotHandled
from haystack.utils import loading
from haystack.utils.app_loading import haystack_get_models, haystack_load_apps

from coredata.queries import SIMSConn, SIMSProblem
from courselib.search import haystack_update_index, haystack_rebuild_index
from courselib.svn import update_repository
from django.core.management import call_command
from courselib.celerytasks import task
from coredata.models import Role, Unit, EnrolmentHistory
import celery

app = celery.Celery(broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)  # periodic tasks don't fire without app constructed


# the maximum beat test age we'd be happy with
BEAT_FILE_MAX_AGE = 1200

# hack around dealing with long chains https://github.com/celery/celery/issues/1078
import sys
sys.setrecursionlimit(10000)

@task(rate_limit="30/m", max_retries=2)
def update_repository_task(*args, **kwargs):
    return update_repository(*args, **kwargs)


# system tasks

@task(queue='fast')
def ping(): # used to check that celery is alive
    return True


@task(queue='email')
def email_queue_ping(): # used to check that the celery email queue is alive
    return True


@task(queue='fast')
def failing_task(): # used to check celery error handling
    raise RuntimeError('This is a deliberately-thrown exception to test exception-handling from a Celery task. It can be ignored.')


# a periodic job that has enough of an effect that we can see celerybeat working
# (checked by ping_celery management command)
@task()
def beat_test():
    set_beat_time()


def get_beat_time() -> int:
    """
    Retrieve most recent celery beat marker.
    """
    # need to record the celery beat time in the DB so we can retrieve and update it as necessary.
    # This seems like the least-stupid place.
    u = Unit.objects.get(slug='univ')
    try:
        return u.config['celery-beat-time']
    except KeyError:
        return 0


def beat_time_okay() -> bool:
    """
    Is the most-recent run of beat_test acceptable?
    """
    last = get_beat_time()
    now = time.time()
    return now - last <= BEAT_FILE_MAX_AGE


def set_beat_time() -> None:
    """
    Set celery beat marker to the current unix time.
    """
    u = Unit.objects.get(slug='univ')
    u.config['celery-beat-time'] = int(time.time())
    u.save()


@task()
def regular_backup():
    backup_database.si().apply_async()


@task()
def backup_database():
    call_command('backup_db', clean_old=True)


@task()
def check_sims_connection():
    if settings.DISABLE_REPORTING_DB:
        return
    from coredata.queries import SIMSConn, SIMSProblem
    db = SIMSConn()
    db.execute("SELECT DESCR FROM PS_TERM_TBL WHERE STRM='1111'", ())
    if len(list(db)) == 0:
        raise SIMSProblem("Didn't get any data back from SIMS query.")


@task(queue='sims')
def check_sims_task() -> Optional[str]:
    """
    Check SIMS queries for sanity, when run in a Celery task. Returns None if successful, or an error message.
    """
    try:
        db = SIMSConn()
        db.execute("SELECT LAST_NAME FROM PS_NAMES WHERE EMPLID='301355288'", ())
        result = list(db)
        # whoever this is, they have non-ASCII in their name: let's hope they don't change it.
        lname = result[0][0]
        if not isinstance(lname, str):
            return 'string result not a string: check Unicode decoding'
        elif lname[1] != u'\u00e4':
            return 'returned incorrectly-decoded Unicode'
        elif len(result) == 0:
            return 'query inexplicably returned nothing'
        else:
            return None
    except SIMSProblem as e:
        return 'SIMSProblem, %s' % (str(e),)
    except ImportError:
        return "couldn't import DB2 module"
    except Exception as e:
        return 'Generic exception, %s' % (str(e))


@task()
def expiring_roles():
    if settings.DO_IMPORTING_HERE:
        Role.warn_expiring()
    Role.purge_expired()


@task()
def expire_sessions_conveniently():
    """
    Expire sessions before the full SESSION_COOKIE_AGE, but at a convenient time, so session don't disappear in the
    middle of a workday.
    """
    hour = datetime.datetime.now().hour
    if not (2 < hour < 6):
        # If the task gets run at the wrong time (because celery was down or something), bail out. The whole point
        # is to expire sessions at convenient times, so let's not fail at that. Worst case: inconvenient expiry
        # after the full session length.
        return

    from importlib import import_module
    engine = import_module(settings.SESSION_ENGINE)
    session_store_class = engine.SessionStore.get_model_class()
    cutoff = datetime.datetime.now() + datetime.timedelta(seconds=settings.PRE_EXPIRE_AGE)
    expires_soon = session_store_class.objects.filter(expire_date__lte=cutoff)
    expires_soon.delete()


import logging
logger = logging.getLogger(__name__)


# daily import tasks

from django.conf import settings
from coredata.models import CourseOffering, Member
from dashboard.models import NewsItem
from log.models import LogEntry, EventLogEntry
from coredata import importer
import itertools, datetime, time
import logging
logger = logging.getLogger('coredata.importer')


# adapted from https://docs.python.org/2/library/itertools.html
# Used to chunk big lists into task-sized blocks.
def grouper(iterable, n):
    """
    Collect data into fixed-length chunks or blocks
    grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    """
    args = [iter(iterable)] * n
    groups = itertools.zip_longest(fillvalue=None, *args)
    return ((v for v in grp if v is not None) for grp in groups)


@task()
def daily_import():
    """
    Start the daily import work.
    """
    # This is a separate task because periodic tasks run in the worker queue. We want all SIMS access running in the
    # sims queue. This task essentially starts and bounces the work into the other queue.
    if not settings.DO_IMPORTING_HERE:
        return

    import_task.apply_async()


@task(queue='sims')
def import_task():
    """
    Enter all of the daily import tasks into the queue, where they can grind away from there.

    The import is broken up into tasks for a few reasons: it can be paused by stopping the sims queue if necessary;
    works around the celery task time limit.
    """
    if not settings.DO_IMPORTING_HERE:
        return

    tasks = [
        daily_cleanup.si(),
        fix_unknown_emplids.si(),
        get_role_people.si(),
        import_offerings.si(continue_import=True),
        import_semester_info.si(),
        import_active_grad_gpas.si(),
    ]

    celery.chain(*tasks).apply_async(serializer='pickle')


@task(queue='sims')
def fix_unknown_emplids():
    logger.info('Fixing unknown emplids')
    importer.fix_emplid()


@task(queue='sims')
def get_role_people():
    logger.info('Importing people with roles')
    importer.get_role_people()

@task(queue='sims')
def import_offerings(continue_import=False):
    logger.info('Fetching offerings')
    #tasks = get_import_offerings_tasks()
    #logger.info('Starting offering subtasks')
    #for t in tasks:
    #    t.apply_async()

    tasks = get_import_offerings_tasks()

    if continue_import:
        tasks = tasks | import_combined_sections.si()
        tasks = tasks | import_joint.si()
        tasks = tasks | haystack_update.si()

    logger.info('Starting offering subtasks')
    tasks.apply_async()


def get_import_offerings_tasks():
    """
    Get all of the offerings to import, and build tasks (in groups) to do the work.

    Doesn't actually call the jobs: just returns celery tasks to be called.
    """
    #offerings = importer.import_offerings(extra_where="CT.SUBJECT='CMPT' and CT.CATALOG_NBR IN (' 383', ' 470')")
    offerings = importer.import_offerings(cancel_missing=True)
    offerings = list(offerings)
    offerings.sort()

    offering_groups = grouper(offerings, 10)
    slug_groups = ([o.slug for o in offerings] for offerings in offering_groups)

    #tasks = [import_offering_group.si(slugs) for slugs in slug_groups]
    #return tasks

    offering_import_chain = celery.chain(*[import_offering_group.si(slugs) for slugs in slug_groups])
    return offering_import_chain

from requests.exceptions import Timeout
@task(bind=True, queue='sims', default_retry_delay=300)
def import_offering_group(self, slugs):
    offerings = CourseOffering.objects.filter(slug__in=slugs)
    for o in offerings:
        logger.debug('Importing %s' % (o.slug,))
        try:
            importer.import_offering_members(o)
        except Timeout as exc:
            # elasticsearch timeout: have celery pause while it collects it thoughts, and retry
            raise self.retry(exc=exc)


@task(queue='sims')
def import_combined_sections():
    logger.info('Importing combined sections from SIMS')
    importer.import_combined()

@task(queue='sims')
def import_joint():
    logger.info('Importing joint offerings from SIMS')
    importer.import_joint()

@task(queue='sims')
def import_semester_info():
    logger.info('Importing semester info')
    importer.import_semester_info()


@task(queue='sims')
def daily_cleanup():
    logger.info('Cleaning up database')
    # cleanup sessions table
    call_command('clearsessions')
    call_command('django_cas_ng_clean_sessions')
    # cleanup old news items
    NewsItem.objects.filter(updated__lt=datetime.datetime.now()-datetime.timedelta(days=365)).delete()
    # cleanup old log entries
    LogEntry.objects.filter(datetime__lt=datetime.datetime.now()-datetime.timedelta(days=365)).delete()
    # cleanup old official grades
    Member.clear_old_official_grades()
    # cleanup old similarity reports
    from submission.models.base import SimilarityResult
    SimilarityResult.cleanup_old()
    # deduplicate EnrolmentHistory
    EnrolmentHistory.deduplicate(start_date=datetime.date.today() - datetime.timedelta(days=30))
    # purge old EventLogs
    EventLogEntry.purge_old_logs()
    # clear orphaned tmp files
    cleanup_tmp()


def cleanup_tmp(path: str = '/tmp'):
    """
    Remove any old temporary files. (They can be left by aborted .zip file downloads.)
    """
    uid = os.getuid()
    now = time.time()
    maxage = 2 * 24 * 3600  # 2 days
    for f in os.listdir(path):
        fp = os.path.join(path, f)
        st = os.stat(fp)
        # only files owned by us
        if not os.path.isfile(fp) or st.st_uid != uid:
            continue
        # only files not accessed recently
        age = now - st.st_atime
        if age < maxage:
            continue
        os.remove(os.path.join(path, f))


@task(queue='sims')
def import_active_grad_gpas():
    logger.info('Importing active grad GPAs')
    importer.import_active_grads_gpas()


###################################################################################################
# Search-related tasks


@task(queue='sims')
def haystack_update():
    haystack_update_index()


# purge and rebuild the search index occasionally to get any orphaned records
@task(queue='sims')
def haystack_rebuild():
    haystack_rebuild_index()


@task(queue='batch')
def our_update_index(group_size: int = 2500, update_only: bool = True):
    """
    Roughly equivalent to the Haystack update_index management command, but handles the work in reasonably-sized
    Celery tasks.
    group_size: the number of objects to index in a task
    update_only: don't necessarily index *everything*. Honour the SearchIndex's .update_filter() method if present.
    """
    haystack_connections = loading.ConnectionHandler(settings.HAYSTACK_CONNECTIONS)
    backends = haystack_connections.connections_info.keys()
    for label in haystack_load_apps():
        for using in backends:
            unified_index = haystack_connections[using].get_unified_index()
            for model in haystack_get_models(label):
                try:
                    index = unified_index.get_index(model)
                except NotHandled:
                    continue

                qs = index.build_queryset(using=using)

                if update_only and hasattr(index, 'update_filter'):  # allow updating of only-likely-changing instances
                    qs = index.update_filter(qs)

                tasks = []
                for group in grouper(qs.values('pk'), group_size):
                    t = update_index_chunk.si(using=using, model=model, pks=[o['pk'] for o in group])
                    tasks.append(t)
                chain = celery.chain(*tasks)
                chain.delay()


@task(queue='batch', serializer='pickle')
def update_index_chunk(using: str, model: Type[models.Model], pks: Iterable[int], commit: bool = True) -> None:
    """
    Index these instances (type model, primary keys in pks) with Haystack.
    """
    haystack_connections = loading.ConnectionHandler(settings.HAYSTACK_CONNECTIONS)
    backend = haystack_connections[using].get_backend()
    unified_index = haystack_connections[using].get_unified_index()
    index = unified_index.get_index(model)
    qs = model.objects.filter(pk__in=pks)
    backend.update(index, qs, commit=commit)
