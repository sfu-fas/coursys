from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
import django
import celery
from coredata.tasks import ping
from coredata.models import Semester, Unit
from coredata.queries import SIMSConn, SIMSProblem
from dashboard.photos import do_photo_fetch
from optparse import make_option
import random, subprocess, socket, urllib2
import os, stat

class Command(BaseCommand):
    help = 'Check the status of the various things we rely on in deployment.'
    option_list = BaseCommand.option_list + (
        make_option('--cache_subcall',
            dest='cache_subcall',
            action='store_true',
            default=False,
            help="Called only as part of check_things. Doesn't do anything useful on its own."),
        make_option('--email',
            dest='email',
            default='',
            help="Email this address to make sure it's sent."),
        )

    def _report(self, title, reports):
        if reports:
            self.stdout.write('\n%s:\n' % (title))
        for criteria, message in reports:
            self.stdout.write('  %s: %s' % (criteria, message))

    def _last_component(self, s):
        return s.split('.')[-1]

    def check_cert(self, filename):
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

    def handle(self, *args, **options):
        if options['cache_subcall']:
            # add one to the cached value, so the main process can tell we see/update the same cache
            res = cache.get('check_things_cache_test', -100)
            cache.set('check_things_cache_test', res + 1)
            return

        info = []
        passed = []
        failed = []
        unknown = []

        # informational data
        info.append(('Deploy mode', settings.DEPLOY_MODE))
        info.append(('Database engine', self._last_component(settings.DATABASES['default']['ENGINE'])))
        info.append(('Cache backend', self._last_component(settings.CACHES['default']['BACKEND'])))
        info.append(('Haystack engine', self._last_component(settings.HAYSTACK_CONNECTIONS['default']['ENGINE'])))
        info.append(('Email backend', '.'.join(settings.EMAIL_BACKEND.split('.')[-2:])))
        if settings.CELERY_EMAIL:
            info.append(('Celery email backend', '.'.join(settings.CELERY_EMAIL_BACKEND.split('.')[-2:])))
        info.append(('Celery broker', settings.BROKER_URL.split(':')[0]))



        # email sending
        if options['email']:
            email = options['email']
            try:
                send_mail('check_things test message', "This is a test message to make sure they're getting through.",
                          settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
                unknown.append(('Email sending', "message sent to %s." % (email)))
            except socket.error:
                failed.append(('Email sending', "socket error: maybe can't communicate with AMPQ for celery sending?"))
        else:
            unknown.append(('Email sending', "provide an --email argument to test."))

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

        # compression enabled?
        if settings.COMPRESS_ENABLED:
            passed.append(('Asset compression enabled', 'okay'))
        else:
            failed.append(('Asset compression enabled', 'disabled in settings'))

        # Haystack searching
        from haystack.query import SearchQuerySet
        res = SearchQuerySet().filter(text='cmpt')
        if res:
            passed.append(('Haystack search', 'okay'))
        else:
            failed.append(('Haystack search', 'nothing found: maybe update_index, or wait for search server to fully start'))


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

        # certificates
        bad_cert = 0
        res = self.check_cert('/etc/stunnel/stunnel.pem')
        if res:
            failed.append(('Stunnel cert', res))
            bad_cert += 1
        res = self.check_cert('/etc/nginx/cert.pem')
        if res:
            failed.append(('SSL PEM', res))
            bad_cert += 1
        res = self.check_cert('/etc/nginx/cert.key')
        if res:
            failed.append(('SSL KEY', res))
            bad_cert += 1

        if bad_cert == 0:
            passed.append(('Certificates', 'All okay, but maybe check http://www.digicert.com/help/'))

        # TODO: svn database, amaint database

        # report results
        self._report('For information', info)
        self._report('These checks passed', passed)
        self._report('These checks failed', failed)
        self._report('Status unknown', unknown)
        self.stdout.write('\n')


