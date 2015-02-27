from django.core.management.base import BaseCommand
from coredata.models import Unit
from grad.importer import NEW_create_or_update_student, NEW_import_unit_grads

class Command(BaseCommand):
    def handle(self, *args, **options):
        unit_slug = args[0]
        #from courselib.testing import create_fake_semester
        #import itertools
        #strms = itertools.product(map(lambda y: "%03i"%(y), range(98, 114)), ['1', '4', '7'])
        #for yr,s in strms:
        #    strm = yr+s
        #    create_fake_semester(strm)

        NEW_import_unit_grads(Unit.objects.get(slug=unit_slug), dry_run=True)