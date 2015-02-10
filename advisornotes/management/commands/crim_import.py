from django.core.management.base import BaseCommand
import unicodecsv as csv
import datetime

from advisornotes.models import AdvisorNote
from coredata.models import Person, Unit
from coredata.queries import add_person

unit = Unit.objects.get(slug='crim')

class Command(BaseCommand):
    help = 'Import CSV advising data from CRIM.'
    args = '<advisor_userid> <csv_data>'

    def import_note(self, advisor, row):
        emplid = row[4]
        fn_transcript = row[3]
        fn_1 = row[6]
        fn_2 = row[7]
        fn_3 = row[9]
        email = row[10]
        date_str = row[12]

        if not emplid:
            return

        p = add_person(emplid)
        if not p:
            return

        created = datetime.datetime.strptime(date_str, '%m-%d-%Y')

        note = AdvisorNote(student=p, advisor=advisor, created_at=created, unit=unit)
        print note


    def import_notes(self, advisor_userid, inputfile):
        advisor = Person.objects.get(userid=advisor_userid)
        with open(inputfile, 'rb') as fh:
            data = csv.reader(fh, encoding='utf-8')

            headers = data.next()
            assert headers[1] == 'Student'
            assert headers[3] == 'Transcript'
            assert headers[4] == 'Student ID'
            assert headers[6] == 'Files'
            assert headers[7] == 'Files2'
            assert headers[9] == 'Files3'
            assert headers[10] == 'Email'
            assert headers[12] == 'Date Modified'

            for row in data:
                self.import_note(advisor, row)


    def handle(self, *args, **options):
        self.import_notes(args[0], args[1])