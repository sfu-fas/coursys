from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
import django

from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape

from coredata.models import Semester, Unit
from coredata.queries import SIMSConn, SIMSProblem, userid_to_emplid, csrpt_update
from dashboard.photos import do_photo_fetch

import celery
import random, socket, subprocess, urllib2, os, stat, time, copy, pprint


def _last_component(s):
    return s.split('.')[-1]

def _check_cert(filename):
    """
    Does this certificate file look okay?

    Returns error message, or None if okay
    """
    try:
        st = os.stat(filename)
    except OSError:
        return filename + " doesn't exist"
    else:
        good_perm = stat.S_IFREG | stat.S_IRUSR # | stat.S_IWUSR
        if (st[stat.ST_UID], st[stat.ST_GID]) != (0,0):
            return 'not owned by root.root'
        perm = st[stat.ST_MODE]
        if good_perm != perm:
            return "expected permissions %o but found %o." % (good_perm, perm)

def _check_file_create(directory):
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



def settings_info():
    info = []
    info.append(('Deploy mode', settings.DEPLOY_MODE))
    info.append(('Database engine', settings.DATABASES['default']['ENGINE']))
    info.append(('Cache backend', settings.CACHES['default']['BACKEND']))
    info.append(('Haystack engine', settings.HAYSTACK_CONNECTIONS['default']['ENGINE']))
    info.append(('Email backend', settings.EMAIL_BACKEND))
    if hasattr(settings, 'CELERY_EMAIL') and settings.CELERY_EMAIL:
        info.append(('Celery email backend', settings.CELERY_EMAIL_BACKEND))
    if hasattr(settings, 'BROKER_URL'):
        info.append(('Celery broker', settings.BROKER_URL.split(':')[0]))

    DATABASES = copy.deepcopy(settings.DATABASES)
    for d in DATABASES:
        if 'PASSWORD' in DATABASES[d]:
            DATABASES[d]['PASSWORD'] = '*****'
    info.append(('DATABASES',  mark_safe('<pre>'+escape(pprint.pformat(DATABASES))+'</pre>')))

    return info


def deploy_checks(request=None):
    passed = []
    failed = []

    # cache something now to see if it's still there further down.
    randval = random.randint(1, 1000000)
    cache.set('check_things_cache_test', randval, 60)

    # Django database
    try:
        n = Semester.objects.all().count()
        if n > 0:
            passed.append(('Main database connection', 'okay'))
        else:
            failed.append(('Main database connection', "Can't find any coredata.Semester objects"))
    except django.db.utils.OperationalError:
        failed.append(('Main database connection', "can't connect to database"))
    except django.db.utils.ProgrammingError:
        failed.append(('Main database connection', "database tables missing"))

    # Celery tasks
    celery_okay = False
    try:
        if settings.USE_CELERY:
            try:
                from coredata.tasks import ping
            except ImportError:
                failed.append(('Celery task', "Couldn't import task: probably missing MySQLdb module"))
            else:
                t = ping.apply_async()
                res = t.get(timeout=5)
                if res == True:
                    passed.append(('Celery task', 'okay'))
                    celery_okay = True
                else:
                    failed.append(('Celery task', 'got incorrect result from task'))
        else:
            failed.append(('Celery task', 'celery disabled in settings'))
    except celery.exceptions.TimeoutError:
        failed.append(('Celery task', "didn't get result before timeout: celeryd maybe not running"))
    except socket.error:
        failed.append(('Celery task', "can't communicate with broker"))
    except NotImplementedError:
        failed.append(('Celery task', 'celery disabled'))
    except django.db.utils.ProgrammingError:
        failed.append(('Celery task', 'celery DB tables missing'))
    except django.db.utils.OperationalError:
        failed.append(('Celery task', 'djkombu tables missing: try migrating'))

    # celery beat
    try:
        from coredata.tasks import BEAT_TEST_FILE, BEAT_FILE_MAX_AGE
        beatfile_age = time.time() - os.stat(BEAT_TEST_FILE).st_mtime
        if beatfile_age < BEAT_FILE_MAX_AGE:
            passed.append(('Celery beat', 'okay'))
        else:
            failed.append(('Celery beat', 'marker file is old: celery beat likely not processing tasks'))
    except OSError:
        failed.append(('Celery beat', 'marker file is missing: celery beat likely not processing tasks'))

    # Django cache
    # (has a subprocess do something to make sure we're in a persistent shared cache, not DummyCache)
    subprocess.call(['python', 'manage.py', 'check_things', '--cache_subcall'])
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
        db.execute("SELECT last_name FROM ps_names WHERE emplid=200133427", ())
        n = len(list(db))
        if n > 0:
            passed.append(('Reporting DB connection', 'okay'))
        else:
            failed.append(('Reporting DB connection', 'query inexplicably returned nothing'))
    except SIMSProblem as e:
        failed.append(('Reporting DB connection', 'SIMSProblem, %s' % (unicode(e))))
    except ImportError:
        failed.append(('Reporting DB connection', "couldn't import DB2 module"))

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
    if cache_okay and celery_okay:
        try:
            res = do_photo_fetch(['301222726'])
            if '301222726' not in res: # I don't know who 301222726 is, but he/she is real.
                failed.append(('Photo fetching', "didn't find photo we expect to exist"))
            else:
                passed.append(('Photo fetching', 'okay'))
        except (KeyError, Unit.DoesNotExist, django.db.utils.ProgrammingError):
            failed.append(('Photo fetching', 'photo password not set'))
        except urllib2.HTTPError as e:
            failed.append(('Photo fetching', 'failed to fetch photo (%s). Maybe wrong password?' % (e)))
    else:
        failed.append(('Photo fetching', 'not testing since memcached or celery failed'))

    # emplid/userid API
    emplid = userid_to_emplid('ggbaker')
    if not emplid:
        failed.append(('Emplid API', 'no emplid returned'))
    elif isinstance(emplid, basestring) and not emplid.startswith('2000'):
        failed.append(('Emplid API', 'incorrect emplid returned'))
    else:
        passed.append(('Emplid API', 'okay'))

    # Piwik API
    #if not request:
    #    failed.append(('Piwik API', "can only check in web frontend with valid request object"))
    #elif not settings.PIWIK_URL or not settings.PIWIK_TOKEN:
    #    failed.append(('Piwik API', "not configured in secrets.py"))
    #else:
    #    # try to re-log this request in piwik and see what happens
    #    from piwik_middleware.tracking import PiwikTrackerLogic, urllib_errors
    #    tracking_logic = PiwikTrackerLogic()
    #    kwargs = tracking_logic.get_track_kwargs(request)
    #    try:
    #        tracking_logic.do_track_page_view(fail_silently=False, **kwargs)
    #    except urllib_errors as e:
    #        failed.append(('Piwik API', "API call failed: %s" % (e)))
    #    else:
    #        passed.append(('Piwik API', 'okay'))

    # Backup server
    if not settings.BACKUP_SERVER or not settings.BACKUP_USER or not settings.BACKUP_PATH or not settings.BACKUP_PASSPHRASE:
        failed.append(('Backup server', 'Backup server settings not all present'))
    else:
        from coredata.management.commands.backup_remote import do_check
        try:
            do_check()
        except RuntimeError as e:
            failed.append(('Backup server', unicode(e)))
        passed.append(('Backup server', 'okay'))


    # certificates
    bad_cert = 0
    res = _check_cert('/etc/stunnel/stunnel.pem')
    if res:
        failed.append(('Stunnel cert', res))
        bad_cert += 1
    res = _check_cert('/etc/nginx/cert.pem')
    if res:
        failed.append(('SSL PEM', res))
        bad_cert += 1
    res = _check_cert('/etc/nginx/cert.key')
    if res:
        failed.append(('SSL KEY', res))
        bad_cert += 1

    if bad_cert == 0:
        passed.append(('Certificates', 'All okay, but maybe check http://www.digicert.com/help/ or https://www.ssllabs.com/ssltest/'))

    # SVN database
    if settings.SVN_DB_CONNECT:
        from courselib.svn import SVN_TABLE, _db_conn
        import MySQLdb
        try:
            db = _db_conn()
            db.execute('SELECT count(*) FROM '+SVN_TABLE, ())
            n = list(db)[0][0]
            if n > 0:
                passed.append(('SVN database', 'okay'))
            else:
                failed.append(('SVN database', "couldn't access records"))
        except MySQLdb.OperationalError:
            failed.append(('SVN database', "can't connect to database"))
    else:
        failed.append(('SVN database', 'SVN_DB_CONNECT not set in secrets.py'))

    # file creation in the necessary places
    dirs_to_check = [
        (settings.DB_BACKUP_DIR, 'DB backup dir'),
        (settings.SUBMISSION_PATH, 'submitted files path'),
        (os.path.join(settings.COMPRESS_ROOT, 'CACHE'), 'compressed media root'),
    ]
    for directory, label in dirs_to_check:
        res = _check_file_create(directory)
        if res is None:
            passed.append(('File creation in ' + label, 'okay'))
        else:
            failed.append(('File creation in ' + label, res))

    # are any services listening publicly that shouldn't?
    hostname = socket.gethostname()
    ports = [
        25, # mail server
        #4369, # epmd, erlang port mapper daemon is okay to listen externally and won't start with ERL_EPMD_ADDRESS set. http://serverfault.com/questions/283913/turn-off-epmd-listening-port-4369-in-ubuntu-rabbitmq
        45130, # beam? rabbitmq something
        4000, # main DB stunnel
        50000, # reporting DB
        8000, # gunicorn
        11211, # memcached
        9200, 9300, # elasticsearch
    ]
    connected = []
    for p in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((hostname, p))
        except socket.error:
            # couldn't connect: good
            pass
        else:
            connected.append(p)
        finally:
            s.close()

    if connected:
        failed.append(('Ports listening externally', 'got connections to port ' + ','.join(str(p) for p in connected)))
    else:
        passed.append(('Ports listening externally', 'okay'))


    return passed, failed


def send_test_email(email):
    try:
        send_mail('check_things test message', "This is a test message to make sure they're getting through.",
                  settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        return True, "Message sent to %s." % (email)
    except socket.error:
        return False, "socket error: maybe can't communicate with AMPQ for celery sending?"

def git_branch():
    return subprocess.check_output(['git', 'rev-parse', '--symbolic-full-name', '--abbrev-ref', 'HEAD'])

def git_revision():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'])

def celery_info():
    from celery.task.control import inspect
    i = inspect()
    info = []
    active = i.active()
    if not active:
        return [('Error', 'Could not inspect Celery: it may be down.')]
    for worker, tasks in active.items():
        if tasks:
            taskstr = '; '.join("%s(*%s, **%s)" % (t['name'], t['args'], t['kwargs'])
                       for t in tasks)
        else:
            taskstr = 'None'

        info.append((worker + ' active', taskstr))

    for worker, tasks in i.scheduled().items():
        info.append((worker + ' scheduled', len(tasks)))

    info.sort()
    return info

def ps_info():
    import psutil, time
    CMD_DISP_MAX = 80
    data = []
    data.append(('System Load', os.getloadavg()))
    cpu_total = 0
    psdata = ['<table id="procs"><thead><tr><th>PID</th><th>Owner</th><th>CPU %</th><th>VM Use (MB)</th><th>Status</th><th>Command</th></tr></thead><tbody>']
    for proc in psutil.process_iter():
        # start the clock on CPU usage percents
        try:
            proc.cpu_percent()
        except psutil.NoSuchProcess:
            pass

    time.sleep(2)
    for proc in psutil.process_iter():
        try:
            perc = proc.cpu_percent()
            if perc > 0:
                cpu_total += perc
                mem = proc.memory_info().vms / 1024.0 / 1024.0
                cmd = ' '.join(proc.cmdline())
                if len(cmd) > CMD_DISP_MAX:
                    cmd = '<span title="%s">%s</span>' % (escape(cmd), escape(cmd[:(CMD_DISP_MAX-5)]) + '&hellip;')
                else:
                    cmd = escape(cmd)

                psdata.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%.1f</td><td>%s</td><td>%s</td></tr>' \
                    % (proc.pid, proc.username(), perc, mem, escape(unicode(proc.status())), cmd))

        except psutil.NoSuchProcess:
            pass
    psdata.append('</tbody></table>')
    data.append(('CPU Percent', cpu_total))
    data.append(('Running Processes', mark_safe(''.join(psdata))))
    return data

def pip_info():
    pip = subprocess.Popen(['pip', 'freeze'], stdout=subprocess.PIPE)
    output = pip.stdout.read()
    result = '<pre>' + escape(output) + '</pre>'
    return [('PIP freeze', mark_safe(result))]

def csrpt_info():
    try:
        return csrpt_update()
    except SIMSProblem as e:
        return [('SIMS problem', str(e))]
