from django.conf import settings
from courselib.svn import update_repository
from coredata.management.commands import backup_db
from celery.task import task, periodic_task
from celery.schedules import crontab

# hack around dealing with long chains https://github.com/celery/celery/issues/1078
import sys
sys.setrecursionlimit(10000)

from celery import Celery
app = Celery()
app.config_from_object(settings)

@task(rate_limit="30/m", max_retries=2)
def update_repository_task(*args, **kwargs):
    return update_repository(*args, **kwargs)



# system tasks

@app.task(bind=True, queue='fast')
def ping(self): # used to check that celery is alive
    return True

@task(queue='fast')
def ping_oldstyle():
    return True

@periodic_task(run_every=crontab(minute=0, hour='*/3'))
def backup_database():
    if settings.DO_IMPORTING_HERE:
        # if we're not on the "real" database, then don't bother with regular backups
        backup_db.Command().handle(clean_old=True)

@periodic_task(run_every=crontab(minute=0, hour='*/3'))
def check_sims_connection():
    from coredata.queries import SIMSConn, SIMSProblem
    db = SIMSConn()
    db.execute("SELECT descr FROM dbcsown.PS_TERM_TBL WHERE strm='1111'", ())
    if len(list(db)) == 0:
        raise SIMSProblem("Didn't get any data back from SIMS query.")












# daily import tasks

from django.conf import settings
from django.core.management import call_command
from djcelery.models import TaskMeta
from coredata.models import CourseOffering, Member
from dashboard.models import NewsItem
from log.models import LogEntry
from coredata import importer
from celery import chain
from grad.models import GradStudent, STATUS_ACTIVE, STATUS_APPLICANT
import itertools, datetime, time
import logging
logger = logging.getLogger('coredata.importer')

# adapted from https://docs.python.org/2/library/itertools.html
# Used to chunk big lists into task-sized blocks.
def _grouper(iterable, n):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    groups = itertools.izip_longest(fillvalue=None, *args)
    return ((v for v in grp if v is not None) for grp in groups)


@periodic_task(run_every=crontab(minute='0', hour='8'))
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

    The import is broken up into tasks for a few reasons: it can be paused by stopping the sims queue if necssary;
    works around the celery task time limit.
    """
    if not settings.DO_IMPORTING_HERE:
        return

    tasks = [
        daily_cleanup.si(),
        get_amaint_userids.si(),
        fix_unknown_emplids.si(),
        update_all_userids.si(),
        get_update_grads_task(),
        import_offerings.si(continue_import=True),
        #get_import_offerings_task(),
        #import_combined_sections.si(),
        #send_report.si()
    ]

    chain(*tasks).apply_async()


@task(queue='sims')
def get_amaint_userids():
    logger.info('Fetching userids from AMAINT')
    importer.update_amaint_userids()

@task(queue='sims')
def fix_unknown_emplids():
    logger.info('Fixing unknown emplids')
    importer.fix_emplid()

@task(queue='sims')
def update_all_userids():
    logger.info('Updating userids')
    importer.update_all_userids()


def get_update_grads_task():
    """
    Get grad students to import, and build tasks (in groups) to do the work.

    Doesn't actually call the jobs: just returns a celery task to be called.
    """
    active = GradStudent.objects.filter(current_status__in=STATUS_ACTIVE).select_related('person')
    applicants = GradStudent.objects.filter(current_status__in=STATUS_APPLICANT,
                 updated_at__gt=datetime.datetime.now()-datetime.timedelta(days=7)).select_related('person')
    grads = itertools.chain(active, applicants)
    emplids = set(gs.person.emplid for gs in grads)
    emplid_groups = _grouper(emplids, 20)

    grad_import_chain = chain(*[import_grad_group.si(list(emplids)) for emplids in emplid_groups])
    return grad_import_chain

@task(queue='sims')
def import_grad_group(emplids):
    for emplid in emplids:
        logger.debug('Importing grad %s' % (emplid,))
        importer.get_person_grad(emplid)


@task(queue='sims')
def import_offerings(continue_import=False):
    logger.info('Fetching offerings')
    #tasks = get_import_offerings_tasks()
    #logger.info('Starting offering subtasks')
    #for t in tasks:
    #    t.apply_async()

    tasks = get_import_offerings_tasks()

    if continue_import:
        #import_combined_sections.apply_async()
        tasks = tasks | import_combined_sections.si()

    logger.info('Starting offering subtasks')
    tasks.apply_async()


def get_import_offerings_tasks():
    """
    Get all of the offerings to import, and build tasks (in groups) to do the work.

    Doesn't actually call the jobs: just returns celery tasks to be called.
    """
    #offerings = importer.import_offerings(extra_where="ct.subject='CMPT' and ct.catalog_nbr IN (' 383', ' 470')")
    #offerings = importer.import_offerings()
    offerings = importer.import_offerings(cancel_missing=True)
    offerings = list(offerings)
    offerings.sort()

    offering_groups = _grouper(offerings, 10)
    slug_groups = ([o.slug for o in offerings] for offerings in offering_groups)

    #tasks = [import_offering_group.si(slugs) for slugs in slug_groups]
    #return tasks

    offering_import_chain = chain(*[import_offering_group.si(slugs) for slugs in slug_groups])
    return offering_import_chain

from requests.exceptions import Timeout
@app.task(bind=True, queue='sims', default_retry_delay=300)
def import_offering_group(self, slugs):
    offerings = CourseOffering.objects.filter(slug__in=slugs)
    for o in offerings:
        logger.debug('Importing %s' % (o.slug,))
        try:
            importer.import_offering_members(o)
        except Timeout as exc:
            # elasticsearch timeout: have celery pause while it collects it thoughts, and retry
            raise self.retry(exc=exc)

        time.sleep(1)

#@task(queue='sims')
#def XXXimport_one_offering(offering_slug):
#    logger.info('Importing %s' % (offering_slug,))
#    offering = CourseOffering.objects.get(slug=offering_slug)
#    #importer.import_offering_members(offering)

@task(queue='sims')
def import_combined_sections():
    logger.info('Importing combined sections from SIMS')
    importer.import_combined()

@task(queue='sims')
def combine_sections():
    logger.info('Combining locally-combined sections')
    importer.combine_sections(importer.get_combined())

@task(queue='sims')
def daily_cleanup():
    logger.info('Cleaning up database')
    # cleanup sessions table
    call_command('clearsessions')
    # cleanup old news items
    NewsItem.objects.filter(updated__lt=datetime.datetime.now()-datetime.timedelta(days=120)).delete()
    # cleanup old log entries
    LogEntry.objects.filter(datetime__lt=datetime.datetime.now()-datetime.timedelta(days=240)).delete()
    # cleanup old official grades
    Member.clear_old_official_grades()
    # cleanup old celery tasks
    TaskMeta.objects.filter(date_done__lt=datetime.datetime.now()-datetime.timedelta(days=2)).delete()



class ReportSender(object):
    def __init__(self):
        from courselib.amqp_log import Consumer
        self.messages = []
        self.consumer = None
        self.consumer = Consumer(self.collect_msg)

    def consume(self):
        self.consumer.consume_forever()

    def collect_msg(self, msg):
        print msg


@task(queue='sims')
def send_report():
    #sender = ReportSender()
    pass
