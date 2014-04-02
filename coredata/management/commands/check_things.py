from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
import django
import celery
from coredata.tasks import ping
from coredata.models import Semester
from coredata.queries import SIMSConn, SIMSProblem
from optparse import make_option
import random, subprocess, socket


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

    def handle(self, *args, **options):
        if options['cache_subcall']:
            # add one to the cached value, so the main process can tell we see/update the same cache
            res = cache.get('check_things_cache_test', -100)
            cache.set('check_things_cache_test', res + 1)
            return

        passed = []
        failed = []
        unknown = []

        passed.append(('Deploy mode', settings.DEPLOY_MODE))

        # email sending
        if options['email']:
            email = options['email']
            send_mail('check_things test message', "This is a test message to make sure they're getting through.",
                      settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            unknown.append(('Email sending', "message sent to %s." % (email)))
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
        try:
            if settings.USE_CELERY:
                t = ping.apply_async()
                res = t.get(timeout=5)
                if res == True:
                    passed.append(('Celery task', 'okay'))
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
        res = cache.get('check_things_cache_test')
        if res == randval:
            failed.append(('Django cache', 'other processes not sharing cache: DummyCache probably being used instead of memcached'))
        elif res is None:
            failed.append(('Django cache', 'unable to retrieve anything from cache'))
        elif res != randval + 1:
            failed.append(('Django cache', 'unknown result'))
        else:
            passed.append(('Django cache', 'okay'))

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


        # TODO: svn database, amaint database
        # TODO: are SSL certs in the right places with the right permissions?

        # report results
        if passed:
            self.stdout.write('\nThese checks passed:\n')
        for criteria, message in passed:
            self.stdout.write('  %s: %s' % (criteria, message))

        if failed:
            self.stdout.write('\nThese checks failed:\n')
        for criteria, message in failed:
            self.stdout.write('  %s: %s' % (criteria, message))

        if unknown:
            self.stdout.write('\nStatus unknown:\n')
        for criteria, message in unknown:
            self.stdout.write('  %s: %s' % (criteria, message))

        self.stdout.write('\n')


