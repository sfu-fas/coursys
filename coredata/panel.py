import datetime
import http.client
import ssl
from email.utils import parsedate_to_datetime

import psutil
import requests
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
import django

from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape

from coredata.models import Semester, Unit
from coredata.queries import SIMSConn, SIMSProblem, userid_to_emplid, csrpt_update
from dashboard.photos import do_photo_fetch
from log.models import MonitoringDataLog

import celery, kombu, amqp
import random, socket, subprocess, urllib.request, urllib.error, urllib.parse, os, copy, pprint


def check_file_create(directory):
    """
    Check that files can be created in the given directory.

    Returns error message, or None if okay
    """
    filename = os.path.join(directory, 'filewrite-' + str(os.getpid()) + '.tmp')

    if not os.path.isdir(directory):
        return 'directory does not exist'

    try:
        fh = open(filename, 'w')
    except IOError:
        return 'could not write to a file'
    else:
        fh.write('test file: may safely delete')
        fh.close()
        os.unlink(filename)


def check_free_space(directory, label, min_gb):
    try:
        p, f = [], []
        free = psutil.disk_usage(directory).free/1024/1024/1024
        if free > min_gb:
            p.append((f'Space in {label}', f'okay ({free:.1f} GB)'))
        else:
            f.append((f'Space in {label}', f'Low: {free:.1f} GB'))
    except FileNotFoundError:
        f.append((f'Space in {label}', 'directory does not exist'))
    
    return p, f


def settings_info():
    info = []
    info.append(('Deploy mode', settings.DEPLOY_MODE))
    info.append(('Database engine', settings.DATABASES['default']['ENGINE']))
    info.append(('Authentication Backends', settings.AUTHENTICATION_BACKENDS))
    info.append(('Cache backend', settings.CACHES['default']['BACKEND']))
    info.append(('Haystack engine', settings.HAYSTACK_CONNECTIONS['default']['ENGINE']))
    info.append(('Email backend', settings.EMAIL_BACKEND))
    if hasattr(settings, 'CELERY_EMAIL') and settings.CELERY_EMAIL:
        info.append(('Celery email backend', settings.CELERY_EMAIL_BACKEND))
    if hasattr(settings, 'EMAIL_HOST'):
        info.append(('Email host', settings.EMAIL_HOST))

    DATABASES = copy.deepcopy(settings.DATABASES)
    for d in DATABASES:
        if 'PASSWORD' in DATABASES[d]:
            DATABASES[d]['PASSWORD'] = '*****'
    info.append(('DATABASES',  mark_safe('<pre>'+escape(pprint.pformat(DATABASES))+'</pre>')))

    return info


def sanity_checks():
    """
    Checks that *must* pass before we even try to start a gunicorn server or celery worker.
    """
    passed = []
    failed = []

    # Django database
    try:
        Semester.objects.all().count()
        passed.append(('Main database connection', 'okay'))
    except django.db.utils.OperationalError:
        failed.append(('Main database connection', "can't connect to database"))
    except django.db.utils.ProgrammingError:
        failed.append(('Main database connection', "database tables missing"))

    # check that celery broker can be contacted (not if celery workers are up)
    if settings.USE_CELERY:
        from courses.celery import app
        try:
            app.control.inspect().ping()
            passed.append(('Celery broker accessiblity', 'okay'))
        except Exception as e:
            failed.append(('Celery broker accessiblity', f'Failed: {e}'))

    # cache is accessible
    try:
        cache.set('check_things_cache_ping', 0, 60)
    except Exception as e:
        failed.append(('Cache accessiblity', f'Failed: {e}'))

    return passed, failed


def deploy_checks():
    passed, failed = sanity_checks()

    # cache something now to see if it's still there further down.
    randval = random.randint(1, 1000000)
    cache.set('check_things_cache_test', randval, 60)

    # non-BMP Unicode in database
    try:
        l = MonitoringDataLog.objects.create(time=datetime.datetime.now(), duration=datetime.timedelta(0), metric='Unicode Test \U0001F600', value=0.0, data={})
    except OperationalError:
        failed.append(('Unicode handling in database', 'non-BMP character not supported by connection'))
    else:
        l = MonitoringDataLog.objects.get(id=l.id)
        if '\U0001F600' in l.metric:
            passed.append(('Unicode handling in database', 'okay'))
        else:
            failed.append(('Unicode handling in database', 'non-BMP character not stored correctly'))
        l.delete()

    # check that all database tables are utf8mb4, if mysql
    if settings.DATABASES['default']['ENGINE'].endswith('.mysql'):
        from django.apps import apps
        from django.db import connection

        CORRECT_CHARSET = 'utf8mb4'
        CORRECT_COLLATION = 'utf8mb4_unicode_ci'
        JSONFIELD__COLLATION = 'utf8mb4_bin'
        db_name = settings.DATABASES['default']['NAME']

        with connection.cursor() as cursor:
            # check database defaults
            cursor.execute("SELECT @@character_set_database, @@collation_database;")
            row = cursor.fetchone()
            if row != (CORRECT_CHARSET, CORRECT_COLLATION):
                failed.append(('MySQL database charset',
                               'database default CHARACTER SET and COLLATION incorrect (it is %s): consider "ALTER DATABASE %s CHARACTER SET %s COLLATE %s;"'
                               % (row, db_name, CORRECT_CHARSET, CORRECT_COLLATION)))

            # check each table
            table_names = [model._meta.db_table for model in apps.get_models()]
            # inspect table charset and collations, adapted from https://stackoverflow.com/a/1049958/6871666
            cursor.execute('''SELECT T.table_name, CCSA.character_set_name, CCSA.collation_name
                FROM information_schema.`TABLES` T,
                    information_schema.`COLLATION_CHARACTER_SET_APPLICABILITY` CCSA
                WHERE CCSA.collation_name=T.table_collation
                    AND T.table_schema=%s
                    AND T.table_name IN %s
            ''', (db_name, table_names))
            for table, charset, collation in cursor.fetchall():
                if (charset, collation) != (CORRECT_CHARSET, CORRECT_COLLATION):
                    failed.append(('MySQL database charset',
                                   'table %s has incorrect CHARACTER SET and COLLATION: consider "ALTER TABLE %s CHARACTER SET=%s COLLATE=%s;"'
                                   % (table, table, CORRECT_CHARSET, CORRECT_COLLATION)))

            cursor.execute('''SELECT table_name, character_set_name, collation_name
                FROM information_schema.`COLUMNS`
                WHERE table_schema=%s
                    AND (character_set_name IS NOT NULL OR collation_name IS NOT NULL)
                    AND (character_set_name!=%s OR (collation_name!=%s AND collation_name!=%s));
                ''', (db_name, CORRECT_CHARSET, CORRECT_COLLATION, JSONFIELD__COLLATION))
            for table, charset, collation in cursor.fetchall():
                failed.append(('MySQL database charset',
                               'table %s has incorrect CHARACTER SET and COLLATION on a column (%s and %s): consider "ALTER TABLE %s CONVERT TO CHARACTER SET %s COLLATE %s;"'
                               % (table, charset, collation, table, CORRECT_CHARSET, CORRECT_COLLATION)))

    # Celery tasks
    celery_okay = False
    sims_task = None
    try:
        if settings.USE_CELERY:
            try:
                from coredata.tasks import ping, email_queue_ping
            except ImportError:
                failed.append(('Celery task', "Couldn't import task: probably missing MySQLdb module"))
            else:
                try:
                    task = ping.apply_async()
                    email_task = email_queue_ping.apply_async()
                except kombu.exceptions.OperationalError:
                    failed.append(('Celery task', 'Kombu error. Probably RabbitMQ not running.'))
                except amqp.exceptions.AccessRefused:
                    failed.append(('Celery task', 'AccessRefused error. Probably bad RabbitMQ auth details.'))
                else:
                    from coredata.tasks import check_sims_task
                    sims_task = check_sims_task.apply_async() # start here, in case it's slow
                    res = task.get(timeout=5)
                    if res == True:
                        passed.append(('Celery task', 'okay'))
                        celery_okay = True
                    else:
                        failed.append(('Celery task', 'got incorrect result from task'))
                    
                    try:
                        res = email_task.get(timeout=5)
                        if res == True:
                            passed.append(('Celery email task', 'okay'))
                        else:
                            failed.append(('Celery email task', 'got incorrect result from email ping task'))
                    except celery.exceptions.TimeoutError:
                        failed.append(('Celery email task', "didn't get result before timeout: email queue may have stopped"))

        else:
            failed.append(('Celery task', 'celery disabled in settings'))
    except celery.exceptions.TimeoutError:
        failed.append(('Celery task', "didn't get result before timeout: celeryd maybe not running"))
    except socket.error:
        failed.append(('Celery task', "can't communicate with broker"))
    except NotImplementedError:
        failed.append(('Celery task', 'celery failed to start with NotImplementedError'))
    except django.db.utils.ProgrammingError:
        failed.append(('Celery task', 'celery DB tables missing'))
    except django.db.utils.OperationalError:
        failed.append(('Celery task', 'djkombu tables missing: try migrating'))

    # celery beat
    if settings.USE_CELERY:
        try:
            from coredata.tasks import beat_time_okay
            if beat_time_okay():
                passed.append(('Celery beat', 'okay'))
            else:
                failed.append(('Celery beat', 'marker file is old: celery beat likely not processing tasks'))
        except OSError:
            failed.append(('Celery beat', 'marker file is missing: celery beat likely not processing tasks'))

    # Django cache
    # (has a subprocess do something to make sure we're in a persistent shared cache, not DummyCache)
    python = os.environ.get('PYTHON', 'python3')
    subprocess.call([python, 'manage.py', 'check_things', '--cache_subcall'])
    cache_okay = False
    res = cache.get('check_things_cache_test')
    if res == randval:
        failed.append(('Django cache', 'other processes not sharing cache: dummy/local probably being used instead of memcached'))
    elif res is None:
        failed.append(('Django cache', 'unable to retrieve anything from cache'))
    elif res != randval + 1:
        failed.append(('Django cache', 'unknown result'))
    else:
        passed.append(('Django cache', 'okay'))
        cache_okay = True

    # Reporting DB connection
    try:
        db = SIMSConn()
        db.execute("SELECT LAST_NAME FROM PS_NAMES WHERE EMPLID='301355288'", ())
        result = list(db)
        # whoever this is, they have non-ASCII in their name: let's hope they don't change it.
        lname = result[0][0]
        if not isinstance(lname, str):
            failed.append(('Reporting DB connection', 'string result not a string: check Unicode decoding'))
        elif lname[1] != u'\u00e4':
            failed.append(('Reporting DB connection', 'returned incorrectly-decoded Unicode'))
        elif len(result) == 0:
            failed.append(('Reporting DB connection', 'query inexplicably returned nothing'))
        else:
            passed.append(('Reporting DB connection', 'okay'))
    except SIMSProblem as e:
        failed.append(('Reporting DB connection', 'SIMSProblem, %s' % (str(e))))
    except ImportError:
        failed.append(('Reporting DB connection', "couldn't import pyodbc module"))
    except Exception as e:
        failed.append(('Reporting DB connection', 'Generic exception, %s' % (str(e))))

    if settings.USE_CELERY and sims_task and celery_okay:
        # sims_task started above, so we can double-up on any wait
        try:
            res = sims_task.get(timeout=5)
            if res:
                failed.append(('Celery Reporting DB', res))
            else:
                passed.append(('Celery Reporting DB', 'okay'))
        except celery.exceptions.TimeoutError:
            failed.append(('Celery Reporting DB', "didn't get result before timeout: maybe reporting database is slow?"))
    elif sims_task is None:
        failed.append(('Celery Reporting DB', "didn't check because of Celery failure"))

    # compression enabled?
    if settings.COMPRESS_ENABLED:
        passed.append(('Asset compression enabled', 'okay'))
    else:
        failed.append(('Asset compression enabled', 'disabled in settings'))

    # Haystack searching
    from haystack.query import SearchQuerySet
    try:
        res = SearchQuerySet().filter(text='cmpt')
        if res:
            passed.append(('Haystack search', 'okay'))
        else:
            failed.append(('Haystack search', 'nothing found: maybe update_index, or wait for search server to fully start'))
    except IOError:
        failed.append(('Haystack search', "can't read/write index"))

    # photo fetching
    if cache_okay:  # and celery_okay:  >> removed check so celery-photos can be tested on a not-yet-fully-deployed server
        try:
            res = do_photo_fetch(['301222726'], timeout=5)
            if '301222726' not in res: # I don't know who 301222726 is, but they are real.
                failed.append(('Photo fetching', "didn't find photo we expect to exist"))
            else:
                passed.append(('Photo fetching', 'okay'))
        except (KeyError, Unit.DoesNotExist, django.db.utils.ProgrammingError):
            failed.append(('Photo fetching', 'photo password not set'))
        except urllib.error.HTTPError as e:
            failed.append(('Photo fetching', 'failed to fetch photo (%s). Maybe wrong password?' % (e)))
    else:
        failed.append(('Photo fetching', 'not testing since memcached'))

    # emplid/userid API
    emplid = userid_to_emplid('ggbaker')
    if not emplid:
        failed.append(('Emplid API', 'no emplid returned'))
    elif isinstance(emplid, str) and not emplid.startswith('2000'):
        failed.append(('Emplid API', 'incorrect emplid returned'))
    else:
        passed.append(('Emplid API', 'okay'))

    # CAS connectivity
    try:
        url_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        req = url_opener.open(urllib.parse.urljoin(settings.CAS_SERVER_URL, 'login'))
        if req.status != 200:
            failed.append(('CAS Connectivity', 'Expected 200 response from CAS, but got %i' % (req.status,)))
        else:
            passed.append(('CAS Connectivity', 'okay'))
    except (requests.exceptions.ConnectionError, urllib.error.HTTPError) as e:
        failed.append(('CAS Connectivity', 'Could not connect to CAS server: %s' % (e,)))

    # file creation in the necessary places
    os.makedirs(os.path.join(settings.COMPRESS_ROOT, 'CACHE'), mode=0o755, exist_ok=True)
    dirs_to_check = [
        (settings.SUBMISSION_PATH, 'submitted files path'),
        (os.path.join(settings.COMPRESS_ROOT, 'CACHE'), 'compressed media root'),
    ]
    for directory, label in dirs_to_check:
        res = check_file_create(directory)
        if res is None:
            passed.append(('File creation in ' + label, 'okay'))
        else:
            failed.append(('File creation in ' + label, res))
    
    # DB backup directory may only be accessible from that celery worker: that's okay.
    if settings.USE_CELERY and celery_okay and False:  # disabled pending new deploy
        from coredata.tasks import check_db_backup_free
        from coredata.tasks import check_db_backup_create
        taskc = check_db_backup_create.delay(settings.DB_BACKUP_DIR)
        taskf = check_db_backup_free.delay(settings.DB_BACKUP_DIR)
        resc = taskc.get()
        p, f = taskf.get()
    else:
        resc = check_file_create(settings.DB_BACKUP_DIR)
        p, f = check_free_space(settings.DB_BACKUP_DIR, 'DB backup dir', 50)

    if resc is None:
        passed.append(('File creation in DB backup dir', 'okay'))
    else:
        failed.append(('File creation in DB backup dir', resc))
    passed.extend(p)
    failed.extend(f)

    # Check for appropriate free disk space
    p, f = check_free_space('/tmp', '/tmp', 4)
    passed.extend(p)
    failed.extend(f)
    # in prod, we have been running ~7G/month, so this checks for ~1 year of space
    p, f = check_free_space(settings.SUBMISSION_PATH, 'SUBMISSION_PATH', 7*12)
    passed.extend(p)
    failed.extend(f)
    # does / in the container always match the host? It seems to
    p, f = check_free_space('/', 'filesystem root', 20)
    passed.extend(p)
    failed.extend(f)

    # is the server time close to real-time?
    import ntplib
    try:
        c = ntplib.NTPClient()
        response = c.request(settings.NTP_REFERENCE)
        if abs(response.offset) > 0.1:
            failed.append(('Server time', 'Time is %g seconds off NTP reference.' % (response.offset,)))
        else:
            passed.append(('Server time', 'okay'))
    except ntplib.NTPException as e:
        failed.append(('Server time', 'Unable to query NTP reference: %s' % (e,)))

    # library sanity
    err = bitfield_check()
    if err:
        failed.append(('Library sanity', 'django-bitfield: ' + err))
    else:
        err = cache_check()
        if err:
            failed.append(('Library sanity', 'django cache: ' + err))
        else:
            passed.append(('Library sanity', 'okay'))

    # MOSS subprocess
    from submission.moss import check_moss_executable
    check_moss_executable(passed, failed)

    # locale is UTF-8 (matters for the SIMS database connection... or is legacy from DB2?)
    import locale
    _, encoding = locale.getdefaultlocale()
    if encoding == 'UTF-8':
        passed.append(('Locale encoding', 'okay'))
    else:
        failed.append(('Locale encoding', "is %r; should be 'UTF-8'" % (encoding,)))

    return passed, failed


from django.db.utils import OperationalError, ProgrammingError
def bitfield_check():
    """
    The BitField claims it doesn't work in mysql, but what we need has always seemed to be okay. This system check
    makes sure that the subset of behaviour we expect from BitField is there.
    """
    errors = []

    from coredata.models import CourseOffering, OFFERING_FLAG_KEYS
    assert OFFERING_FLAG_KEYS[0] == 'write'

    # find an offering that should be returned by a "flag" query
    try:
        o = CourseOffering.objects.filter(flags=1).first()
    except (OperationalError, ProgrammingError):
        # probably means no DB migration yet: let it slide.
        return []
    if o is None:
        # no data there to check
        return []

    # ... and the filter had better find it
    found = CourseOffering.objects.filter(flags=CourseOffering.flags.write, pk=o.pk)
    if not found:
        return 'Bitfield set-bit query not finding what it should.'
    # ... and the opposite had better not
    found = CourseOffering.objects.filter(flags=~CourseOffering.flags.write, pk=o.pk)
    if found:
        return 'Bitfield negated-bit query finding what it should not.'

    # find an offering that should be returned by a "not flag" query
    o = CourseOffering.objects.filter(flags=0).first()
    # *** This is the one that fails on mysql. We don't use it, so hooray.
    # ... and the filter had better find it
    #found = CourseOffering.objects.filter(flags=~CourseOffering.flags.write, pk=o.pk)
    #if not found:
    #    _add_error(errors, 'Bitfield negated-bit query not finding what it should.', 3)

    # .. and the opposite had better not
    found = CourseOffering.objects.filter(flags=CourseOffering.flags.write, pk=o.pk)
    if found:
        return 'Bitfield set-bit query finding what it should not.'


def cache_check():
    # A version of python-memcached had unicode issues: https://github.com/linsomniac/python-memcached/issues/79
    # Make sure unicode runs through the Django cache unchanged.
    k = 'test_cache_check_key'
    v = '\u2021'
    cache.set(k, v, 30)
    v0 = cache.get(k)
    if v != v0:
        return 'python-memcached butchering Unicode strings'


def send_test_email(email):
    try:
        send_mail('check_things test message', "This is a test message to make sure they're getting through.",
                  settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        return True, "Message sent to %s." % (email)
    except socket.error:
        return False, "socket error: maybe can't communicate with AMPQ for celery sending?"


def celery_info():
    from coredata.tasks import app
    i = app.control.inspect()
    info = []
    active = i.active()
    if not active:
        return [('Error', 'Could not inspect Celery: it may be down.')]
    for worker, tasks in list(active.items()):
        if tasks:
            taskstr = '; '.join("%s(*%s, **%s)" % (t['name'], t['args'], t['kwargs'])
                       for t in tasks)
        else:
            taskstr = 'None'

        info.append((worker + ' active', taskstr))

    for worker, tasks in list(i.scheduled().items()):
        info.append((worker + ' scheduled', len(tasks)))

    info.sort()
    return info


def pip_info():
    pip = subprocess.Popen(['pip3', 'freeze'], stdout=subprocess.PIPE)
    output = pip.stdout.read().decode('utf8')
    result = '<pre>' + escape(output) + '</pre>'
    return [('PIP freeze', mark_safe(result))]


def csrpt_info():
    try:
        return csrpt_update()
    except SIMSProblem as e:
        return [('SIMS problem', str(e))]
