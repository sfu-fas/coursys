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
from django.urls import reverse

from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape

from coredata.models import Semester, Unit
from coredata.queries import SIMSConn, SIMSProblem, userid_to_emplid, csrpt_update
from dashboard.photos import do_photo_fetch
from log.models import LogEntry

import celery, kombu, amqp
import random, socket, subprocess, urllib.request, urllib.error, urllib.parse, os, stat, time, copy, pprint


def _last_component(s):
    return s.split('.')[-1]


def _certificate_expiry(domain: str) -> datetime.datetime:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_OPTIONAL

    conn = http.client.HTTPSConnection(domain, context=context)
    conn.connect()
    cert = conn.sock.getpeercert()

    return parsedate_to_datetime(cert['notAfter'])


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
    info.append(('Authentication Backends', settings.AUTHENTICATION_BACKENDS))
    info.append(('Cache backend', settings.CACHES['default']['BACKEND']))
    info.append(('Haystack engine', settings.HAYSTACK_CONNECTIONS['default']['ENGINE']))
    info.append(('Email backend', settings.EMAIL_BACKEND))
    if hasattr(settings, 'CELERY_EMAIL') and settings.CELERY_EMAIL:
        info.append(('Celery email backend', settings.CELERY_EMAIL_BACKEND))
    if hasattr(settings, 'CELERY_BROKER_URL'):
        info.append(('Celery broker', settings.CELERY_BROKER_URL.split(':')[0]))
    if hasattr(settings, 'EMAIL_HOST'):
        info.append(('Email host', settings.EMAIL_HOST))

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

    # non-BMP Unicode in database
    try:
        l = LogEntry.objects.create(userid='ggbaker', description='Test Unicode \U0001F600', related_object=Semester.objects.first())
    except OperationalError:
        failed.append(('Unicode handling in database', 'non-BMP character not supported by connection'))
    else:
        l = LogEntry.objects.get(id=l.id)
        if '\U0001F600' in l.description:
            passed.append(('Unicode handling in database', 'okay'))
        else:
            failed.append(('Unicode handling in database', 'non-BMP character not stored correctly'))

    # check that all database tables are utf8mb4, if mysql
    if settings.DATABASES['default']['ENGINE'].endswith('.mysql'):
        from django.apps import apps
        from django.db import connection

        CORRECT_CHARSET = 'utf8mb4'
        CORRECT_COLLATION = 'utf8mb4_unicode_ci'
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

            cursor.execute('''SELECT table_name, column_name, character_set_name, collation_name
                FROM information_schema.`COLUMNS`
                WHERE table_schema=%s
                    AND (character_set_name IS NOT NULL OR collation_name IS NOT NULL)
                    AND (character_set_name!=%s OR collation_name!=%s);
                ''', (db_name, CORRECT_CHARSET, CORRECT_COLLATION))
            for table, column, charset, collation in cursor.fetchall():
                failed.append(('MySQL database charset',
                               'table %s has incorrect CHARACTER SET and COLLATION on a column (%s and %s): consider "ALTER TABLE %s CONVERT TO CHARACTER SET %s COLLATE %s;"'
                               % (table, charset, collation, table, CORRECT_CHARSET, CORRECT_COLLATION)))

    # Celery tasks
    celery_okay = False
    sims_task = None
    try:
        if settings.USE_CELERY:
            try:
                from coredata.tasks import ping
            except ImportError:
                failed.append(('Celery task', "Couldn't import task: probably missing MySQLdb module"))
            else:
                try:
                    task = ping.apply_async()
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
    subprocess.call(['python3', 'manage.py', 'check_things', '--cache_subcall'])
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
        failed.append(('Reporting DB connection', "couldn't import DB2 module"))
    except Exception as e:
        failed.append(('Reporting DB connection', 'Generic exception, %s' % (str(e))))

    if settings.USE_CELERY and sims_task:
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
    if cache_okay and celery_okay:
        try:
            res = do_photo_fetch(['301222726'])
            if '301222726' not in res: # I don't know who 301222726 is, but he/she is real.
                failed.append(('Photo fetching', "didn't find photo we expect to exist"))
            else:
                passed.append(('Photo fetching', 'okay'))
        except (KeyError, Unit.DoesNotExist, django.db.utils.ProgrammingError):
            failed.append(('Photo fetching', 'photo password not set'))
        except urllib.error.HTTPError as e:
            failed.append(('Photo fetching', 'failed to fetch photo (%s). Maybe wrong password?' % (e)))
    else:
        failed.append(('Photo fetching', 'not testing since memcached or celery failed'))

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
    except requests.exceptions.ConnectionError as e:
        failed.append(('CAS Connectivity', 'Could not connect to CAS server: %s' % (e,)))

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

    # space in /tmp
    tmp_free = psutil.disk_usage('/tmp').free/1024/1024/1024
    if tmp_free > 4:
        passed.append(('Space in /tmp', 'okay (%.1f GB)' % (tmp_free,)))
    else:
        failed.append(('Space in /tmp', 'Low: %.1f GB' % (tmp_free,)))

    # space in SUBMISSION_PATH
    try:
        sub_free = psutil.disk_usage(settings.SUBMISSION_PATH).free/1024/1024/1024
        # in prod, we have been running ~7G/month, so this checks for ~1 year of space
        if sub_free > 7*12:
            passed.append(('Space in SUBMISSION_PATH', 'okay (%.1f GB)' % (sub_free,)))
        else:
            failed.append(('Space in SUBMISSION_PATH', 'Low: %.1f GB' % (sub_free,)))
    except FileNotFoundError:
        failed.append(('Space in SUBMISSION_PATH', 'directory does not exist'))

    # are any services listening publicly that shouldn't?
    hostname = socket.gethostname()
    ports = [
        #25, # mail server
        #4369, # epmd, erlang port mapper daemon is okay to listen externally and won't start with ERL_EPMD_ADDRESS set. http://serverfault.com/questions/283913/turn-off-epmd-listening-port-4369-in-ubuntu-rabbitmq
        45130, # beam? rabbitmq something
        4000, # main DB stunnel
        50000, # reporting DB
        8000, # gunicorn
        11211, # memcached
        9200, 9300, # elasticsearch
        8983,  # solr
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

    # correct serving/redirecting of production domains
    # TODO: re-enable once we're settled with proxy settings etc
    if False and settings.DEPLOY_MODE in ['production', 'proddev']:
        production_host_fails = 0
        for host in settings.SERVE_HOSTS + settings.REDIRECT_HOSTS:
            # check HTTPS serving/redirect
            try:
                url = 'https://' + host + reverse('docs:list_docs')  # must be a URL that doesn't require auth
                resp = requests.get(url, allow_redirects=False, timeout=5)
                if host in settings.SERVE_HOSTS and resp.status_code != 200:
                    failed.append(('HTTPS Serving', 'expected 200 okay, but got %i at %s' % (resp.status_code, url)))
                    production_host_fails += 1
                elif host in settings.REDIRECT_HOSTS and resp.status_code != 301:
                    failed.append(('HTTPS Serving', 'expected 301 redirect, but got %i at %s' % (resp.status_code, url)))
                    production_host_fails += 1
            except requests.exceptions.SSLError:
                failed.append(('HTTPS Serving', 'bad SSL/TLS certificate for %s' % (url,)))
                production_host_fails += 1
            except requests.exceptions.RequestException:
                failed.append(('HTTPS Serving', 'unable to connect to request %s' % (url,)))
                production_host_fails += 1

            # check HTTP redirect
            try:
                url = 'http://' + host + reverse('docs:list_docs')  # must be a URL that doesn't require auth
                resp = requests.get(url, allow_redirects=False, timeout=5)
                if resp.status_code not in [301, 302]:
                    failed.append(('HTTP Serving', 'expected 301 redirect to https://, but got %i at %s' % (resp.status_code, url)))
                    production_host_fails += 1
            except requests.exceptions.RequestException:
                failed.append(('HTTP Serving', 'unable to connect to request %s' % (url,)))
                production_host_fails += 1

        if production_host_fails == 0:
            passed.append(('HTTPS Serving', 'okay: certs and redirects as expected, but maybe check http://www.digicert.com/help/ or https://www.ssllabs.com/ssltest/'))

        if 'https_proxy' in os.environ:
            failed.append(('Certificate TTL', 'Skipping because https_proxy environment variable is set.'))
        else:
            low_ttl_certs = 0
            min_age = datetime.timedelta(days=14)
            now = datetime.datetime.now(datetime.timezone.utc)
            for host in settings.SERVE_HOSTS + settings.REDIRECT_HOSTS:
                # check that certs aren't expiring soon
                expiry = _certificate_expiry(host)
                if expiry - now < min_age:
                    low_ttl_certs += 1
                    failed.append(('Certificate TTL', 'Certificate for %s expires at %s.' % (host, expiry)))
            if production_host_fails == 0:
                passed.append(('Certificate TTL', 'okay'))

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

    # github-flavoured markdown
    from courselib.github_markdown import markdown_to_html_rpc, markdown_to_html_subprocess
    md = 'test *markup*\n\n```python\nprint(1)\n```\n\u2605\U0001F600'
    correct = '<p>test <em>markup</em></p>\n<pre lang="python"><code>print(1)\n</code></pre>\n<p>\u2605\U0001F600</p>'

    try:
        # checks that ruby subprocess runs; does github-flavour correctly; does Unicode correctly.
        html = markdown_to_html_subprocess(md, fallback=False)
        if html.strip() == correct:
            passed.append(('Markdown subprocess', 'okay'))
        else:
            failed.append(('Markdown subprocess', 'markdown script returned incorrect markup'))
    except OSError:
        failed.append(('Markdown subprocess', 'failed to start ruby command: ruby package probably not installed'))
    except RuntimeError:
        failed.append(('Markdown subprocess', 'markdown script failed'))

    try:
        # checks that docker RPC runs; does github-flavour correctly; does Unicode correctly.
        html = markdown_to_html_rpc(md, fallback=False)
        if html.strip() == correct:
            passed.append(('Markdown RPC', 'okay'))
        else:
            failed.append(('Markdown RPC', 'markdown script returned incorrect markup'))
    except OSError:
        failed.append(('Markdown RPC', 'unable to connect for RPC: docker container may be down'))
    except AttributeError:
        failed.append(('Markdown RPC', 'unable to connect to RabbitMQ: not configured in settings.py'))

    # MOSS subprocess
    from submission.moss import check_moss_executable
    check_moss_executable(passed, failed)

    # locale is UTF-8 (matters for markdown script calls, the SIMS database connection)
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

def git_branch():
    return subprocess.check_output(['git', 'rev-parse', '--symbolic-full-name', '--abbrev-ref', 'HEAD'])

def git_revision():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'])

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
                    % (proc.pid, proc.username(), perc, mem, escape(str(proc.status())), cmd))

        except psutil.NoSuchProcess:
            pass
    psdata.append('</tbody></table>')
    data.append(('CPU Percent', cpu_total))
    data.append(('Running Processes', mark_safe(''.join(psdata))))
    return data

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
