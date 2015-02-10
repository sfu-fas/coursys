from django.core.management.base import BaseCommand
from django.db import transaction
import unicodecsv as csv
import datetime
import os.path

from advisornotes.models import AdvisorNote
from coredata.models import Person, Unit
from coredata.queries import add_person
from courselib.text import normalize_newlines

unit = Unit.objects.get(slug='crim')

class Command(BaseCommand):
    help = 'Import CSV advising data from CRIM.'
    args = '<advisor_userid> <csv_data>'

    def import_note(self, advisor, fn, i, row):
        emplid = row['Student ID']
        #fn_transcript = row['Transcript']
        #fn_1 = row[6]
        #fn_2 = row[7]
        #fn_3 = row[9]
        date_str = row['Date Modified']
        notes = normalize_newlines(row['Notes'])

        # fix mis-typed emplids we found
        # Lindsay
        if emplid == '960022098':
            emplid = '963022098'
        elif emplid == '30108409':
            emplid = '301078409'
        elif emplid == '30115964':
            emplid = '301115964'
        elif emplid == '30117882':
            emplid = '301178882'
        # Michael Sean
        elif emplid == '30105659':
            emplid = '301040985' # ?
        # Dijana
        elif emplid == '30120965':
            emplid = '301202965'


        if not emplid or emplid == '0':
            print 'No emplid on row %i' % (i+2)
            return

        p = add_person(emplid)
        if not p:
            print "Can't find person on row %i (emplid %s)" % (i+2, emplid)
            return

        try:
            date = datetime.datetime.strptime(date_str, '%m-%d-%Y').date()
        except ValueError:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        created = datetime.datetime.combine(date, datetime.time(hour=12, minute=0))

        key = '%s-%i' % (fn, i)

        # look for previously-imported version of this note, so we're roughly idempotent
        oldnotes = AdvisorNote.objects.filter(student=p, advisor=advisor, created_at=created, unit=unit)
        oldnotes = [n for n in oldnotes if 'import_key' in n.config and n.config['import_key'] == key]

        if oldnotes:
            note = oldnotes[0]
        else:
            note = AdvisorNote(student=p, advisor=advisor, created_at=created, unit=unit)

        note.text = notes
        note.config['import_key'] = key
        note.save()


    def import_notes(self, advisor_userid, inputfile):
        advisor = Person.objects.get(userid=advisor_userid)
        with open(inputfile, 'rb') as fh:
            data = csv.DictReader(fh)

            for i, row in enumerate(data):
                with transaction.atomic():
                    self.import_note(advisor, os.path.split(inputfile)[1], i, row)


    def handle(self, *args, **options):
        self.import_notes(args[0], args[1])