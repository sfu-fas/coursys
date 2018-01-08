from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files import File
from optparse import make_option
import unicodecsv as csv
import datetime
import os.path
import mimetypes

from advisornotes.models import AdvisorNote
from coredata.models import Person, Unit
from coredata.queries import add_person
from courselib.text import normalize_newlines

class Command(BaseCommand):
    help = 'Import CSV advising data from CRIM.'
    args = '<unit_slug> <advisor_userid> <csv_data> <file_base>'
    option_list = BaseCommand.option_list + (
        make_option('-n', '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Don\'t actually modify anything.'),
        )

    def get_filepath(self, fm_filename):
        if not fm_filename:
            return None

        filename = os.path.split(fm_filename)[1]
        filepath = os.path.join(self.file_base, filename)

        if os.path.isfile(filepath):
            return filepath
        else:
            if self.verbosity > 0:
                print("Missing file %s." % (filename,))

    def get_advisornote(self, key, person, advisor, created, delete_old_file=False, offset=0):
        """
        get_or_create for this usage
        """
        created = created + datetime.timedelta(minutes=offset)
        # look for previously-imported version of this note, so we're roughly idempotent
        oldnotes = AdvisorNote.objects.filter(student=person, advisor=advisor, created_at=created, unit=self.unit)
        oldnotes = [n for n in oldnotes if 'import_key' in n.config and n.config['import_key'] == key]

        if oldnotes:
            note = oldnotes[0]
            if delete_old_file and note.file_attachment and os.path.isfile(note.file_attachment.path):
                # let file be recreated below
                os.remove(note.file_attachment.path)
                note.file_attachment = None
                note.file_mediatype = None
        else:
            note = AdvisorNote(student=person, advisor=advisor, created_at=created, unit=self.unit)
            note.config['import_key'] = key

        note.config['src'] = 'crim_import'
        return note, bool(oldnotes)

    def attach_file(self, note, filepath):
        """
        Use this filepath as the attachment for this note.
        """
        with File(open(filepath, 'rb')) as fh:
            base = os.path.split(filepath)[1]
            if self.commit:
                note.file_attachment.save(base, fh)

        mediatype = mimetypes.guess_type(filepath)[0]
        note.file_mediatype = mediatype


    def import_note(self, advisor, fn, i, row):
        emplid = row['Student ID']
        date_str = row['Date Modified']
        notes = normalize_newlines(row['Notes'])

        files = [
            row.get('Transcript', None),
            row.get('Files', None),
            row.get('Files2', None),
            row.get('Files3', None),
        ]
        files = list(map(self.get_filepath, files))
        files = list(filter(bool, files))

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
            if self.verbosity > 0:
                print('No emplid on row %i' % (i+2))
            return

        p = add_person(emplid, commit=self.commit)
        if not p:
            if self.verbosity > 0:
                print("Can't find person on row %i (emplid %s)" % (i+2, emplid))
            return

        if self.verbosity > 1:
            print("Importing %s with %i file(s)." % (emplid, len(files)))

        try:
            date = datetime.datetime.strptime(date_str, '%m-%d-%Y').date()
        except ValueError:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        created = datetime.datetime.combine(date, datetime.time(hour=12, minute=0))

        key = '%s-%i' % (fn, i)
        note, _ = self.get_advisornote(key, p, advisor, created, delete_old_file=self.commit)

        if files:
            path = files[0]
            self.attach_file(note, path)

            for j, path in enumerate(files[1:]):
                # these get stashed in accompanying notes
                k = key + '-auxfile-' + str(i)
                n, _ = self.get_advisornote(k, p, advisor, created, delete_old_file=self.commit, offset=(j+1))
                n.text = '[Additional file for previous note.]'
                self.attach_file(n, path)
                if self.commit:
                    n.save()

        note.text = notes
        if self.commit:
            note.save()


    def import_notes(self, unit_slug, advisor_userid, inputfile, file_base):
        self.unit = Unit.objects.get(slug=unit_slug)
        self.file_base = file_base
        advisor = Person.objects.get(userid=advisor_userid)
        with open(inputfile, 'rb') as fh:
            data = csv.DictReader(fh)
            fn = os.path.split(inputfile)[1]

            for i, row in enumerate(data):
                with transaction.atomic():
                    self.import_note(advisor, fn, i, row)


    def handle(self, *args, **options):
        self.verbosity = int(options['verbosity'])
        self.commit = not options['dry_run']
        self.import_notes(args[0], args[1], args[2], args[3])