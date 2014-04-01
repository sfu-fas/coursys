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

    def _expect(self, cond, message=None):
        if cond:
            print 'okay'
        elif message:
            print 'FAIL (%s)' % (message)
        else:
            print 'FAIL'

    def handle(self, *args, **options):
        if options['cache_subcall']:
            res = cache.get('check_things_cache_test', -100)
            cache.set('check_things_cache_test', res + 1)
            return

        if options['email']:
            email = options['email']
            send_mail('check_things test message', "This is a test message to make sure they're getting through.",
                      settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            print "Email sending: sent to %s." % (email)
        else:
            print "Email sending: provide an --email to test."

        # cache something now to see if it's still there further down.
        randval = random.randint(1, 1000000)
        cache.set('check_things_cache_test', randval, 60)

        print "Main database connection:",
        try:
            n = Semester.objects.all().count()
            self._expect(n > 0, message="Can't find any coredata.Semester objects")
        except django.db.utils.OperationalError:
            print "FAIL (can't connect to database)"
        except django.db.utils.ProgrammingError:
            print 'FAIL (database tables missing)'

        print "Celery task:",
        try:
            t = ping.apply_async()
            res = t.get(timeout=5)
            self._expect(res == True)
        except celery.exceptions.TimeoutError:
            print "FAIL (didn't get result before timeout: celeryd maybe not running)"
        except socket.error:
            print "FAIL (can't communicate with broker)"
        except NotImplementedError:
            print 'FAIL (celery disabled)'
        except django.db.utils.ProgrammingError:
            print 'FAIL (celery DB tables missing)'

        print "Django cache:",
        # have a subprocess do something to make sure we're in a persistent shared cache, not DummyCache
        subprocess.call(['python', 'manage.py', 'check_things', '--cache_subcall'])
        res = cache.get('check_things_cache_test')
        self._expect(res == randval+1)

        print "Reporting DB connection:",
        try:
            db = SIMSConn()
            db.execute("SELECT last_name FROM ps_names WHERE emplid=200133427", ())
            n = len(list(db))
            self._expect(n > 0)
        except SIMSProblem as e:
            print 'FAIL (SIMSProblem: ' + unicode(e) + ')'


        # TODO: svn database, amaint database






