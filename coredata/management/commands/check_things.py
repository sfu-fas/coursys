from django.core.management.base import BaseCommand
from django.core.cache import cache
from coredata.tasks import ping
from coredata.models import Semester
from coredata.queries import SIMSConn, SIMSProblem
import random, string, time, subprocess


class Command(BaseCommand):
    help = 'Check the status of the various things we rely on in deployment.'
    def _expect(self, cond):
        if cond:
            print 'okay'
        else:
            print 'FAIL'

    def handle(self, *args, **kwargs):
        randval = random.randint(1, 1000000)
        cache.set('check_things_cache_test', randval, 30)

        print "Main database connection:",
        n = Semester.objects.all().count()
        self._expect(n > 0)

        print "Celery task:",
        t = ping.apply_async()
        res = t.get(timeout=5)
        self._expect(res == True)

        print "Django cache:",
        # have a subprocess do something to make sure we're in a persistent shared cache
        subprocess.call(['python', 'manage.py', 'check_things_sub'])
        res = cache.get('check_things_cache_test')
        self._expect(res == randval+1)

        print "Reporting DB connection:",
        try:
            db = SIMSConn()
            db.execute("SELECT name_type, name_prefix, last_name, first_name, middle_name FROM ps_names WHERE "
                   "emplid=200133427", ())
            n = len(list(db))
        except SIMSProblem:
            n = 0
        self._expect(n > 0)

        # TODO: svn database, amaint database






