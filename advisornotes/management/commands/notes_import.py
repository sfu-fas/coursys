from django.core.management.base import BaseCommand
from django.db import transaction
from advisornotes.models import AdvisorNote
from coredata.models import Person, Unit
from coredata.queries import add_person
import argparse
import csv
import os
from datetime import datetime
from dateutil import parser as dateparser
from courselib.markup import MARKUPS

def get_markup_choices():
    markup_keys = []
    for k, v in MARKUPS.items():
        markup_keys.append(k)
    return ', '.join(markup_keys)

class Command(BaseCommand):
    help = 'Import CSV advising data from a provided file.'
    args = '<unit_slug> <csv_data>'

    def __init__(self, *args, **kwargs):
        # Just defining these because it's good practice to define instance variables in the __init__.
        # Outside of this, these all get set in other methods.
        self.verbose = None
        self.commit = None
        self.file = None
        self.unit_label = None
        self.unit = None
        self.markup = None
        self.saved = 0
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):

        parser.add_argument('input_file', type=argparse.FileType('r'), help='The file to process')
        parser.add_argument('unit', type=str,
                            help='The short name of the unit all the notes will be added under, (e.g. "CMPT")')
        parser.add_argument('--dry-run', '-n',
                            action='store_true',
                            dest='dry_run',
                            help='Don\'t actually save the data',
                            default=False,
                            )
        parser.add_argument('--verbose',
                            action='store_true',
                            dest='verbose',
                            help='Print verbose output.  Same as setting -v > 1',
                            default=False)
        parser.add_argument('--markup', '-m',
                            dest='markup',
                            default='html',
                            help='Choices are: %s.' % get_markup_choices())

    def process_row(self, i, row):
        """
        Actually process each individual row
        """
        row_num = i + 2  #  It's 0 indexed, and we already consumed the header row.
        note_id = row['note_id']
        # Just in case someone had a bunch of trailing slashes, etc, make sure we get solely the file name for the key.
        file_basename = os.path.basename(os.path.normpath(self.file.name))

        # In order for the keys to match (to check for duplicates), they have to have been imported from this importer,
        # from the filename, and with the same note_id.
        key = "notes_import-%s-%s" % (file_basename, note_id)

        # Find the recipient of the note:
        student_emplid = row['emplid']
        p = add_person(student_emplid, commit=self.commit)
        if not p:
            if self.verbose:
                print("ERROR: Can't find recipient on row %i (emplid %s). Ignoring." % (row_num, student_emplid))
            return
        # Find the advisor who entered the note:
        advisor_emplid = row['creator_emplid']
        u = add_person(advisor_emplid, commit=self.commit)
        if not u:
            if self.verbose:
                print("ERROR: Can't find advisor %s on row %i (emplid %s). Ignoring." % (advisor_emplid, row_num, student_emplid))
            return

        read_date = row['date_created']
        # We expect a certain date format, try that first, as the function is slightly faster.
        try:
            date_created = datetime.strptime(read_date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Fine, try to make the dateutils parser figure it out, then.
            try:
                date_created = dateparser.parse(read_date)
            except ValueError:
                if self.verbose:
                    print("ERROR: Cannot deduce the correct date %s at line %i. Ignoring." % (row['date_created'], row_num))
                return

        # Let's check if we've already imported this note (or another which matches):
        matching_notes = AdvisorNote.objects.filter(student=p, advisor=u, created_at=date_created, unit=self.unit)
        key_matching_notes = [n for n in matching_notes if 'import_key' in n.config and n.config['import_key'] == key]
        if key_matching_notes:
            if self.verbose:
                print("Already imported note from this file with note_id %s on row %i, ignoring." % (note_id, row_num))
            return

        # What if we have notes from the exact same time, from the same advisor, for the same recipient, but without
        # a matching key?  That's fishy too.  At first I wrote this to be just a warning and continue processing, but,
        # really, there's no reason a note should match this way.  It serves as a good way to spot files that were
        # already imported under another name.
        if matching_notes.count() != len(key_matching_notes):
            if self.verbose:
                print("Found matching note, but without matching key.  This is fishy.  Note_id %s on row %i. "
                      "Are you sure this file hasn't been processed already using a different filename?  Ignoring "
                      "this note."
                      % (note_id, row_num))
            return

        # We checked every possible case, let's create the new note.
        n = AdvisorNote(student=p, advisor=u, created_at=date_created, unit=self.unit, text=row['notes'])
        n.config['import_key'] = key
        n.markup=self.markup
        if self.verbose:
            print("Creating note for %s from row %i..." % (student_emplid, row_num), end='')
        if self.commit:
            n.save()
            self.saved += 1
            if self.verbose:
                print("Saved.")
        else:
            if self.verbose:
                print("Not saved, dry-run only.")
        return

    def process_file(self):
        try:
            self.unit = Unit.objects.get(label=self.unit_label.upper())
        except Unit.DoesNotExist:
            print("Could not find a unit with the label %s, aborting." % self.unit_label.upper())
            return
        if self.verbose:
            print("Found unit %s." % self.unit)
        csvreader = csv.DictReader(self.file,
                                   fieldnames=["note_id", "emplid", "notes", "date_created", "creator_computing_id",
                                               "creator_emplid"])
        headers=(next(csvreader))
        # Dumb sanity check to make sure we're putting our OrderedDict in the right order.  Since the first
        # row is headers, and we're calling the arguments the same, let's make sure they match.
        for k,v in headers.items():
            if k != v:
                print("Danger, Will Robinson.  Key %s doesn't match value from header row %s.  "
                      "Check your input file.  Aborting." % (k, v))
                return
        if self.verbose:
            print("Headers from file match our dict, starting actual processing.")

        # Another counter to keep track of how many rows we actually saved.
        s = 0
        for i, row in enumerate(csvreader):
            with transaction.atomic():
                self.process_row(i, row)
        if self.verbose:
            print("Processed %i row(s) (ignoring the header row).  Actually saved %i row(s)." % (i + 1, self.saved))

    def handle(self, *args, **options):
        self.verbose = int(options['verbosity']) > 1 or options['verbose']
        self.commit = not options['dry_run']
        self.file = options['input_file']
        self.unit_label = options['unit']
        self.markup = options['markup'].lower()
        if self.markup not in MARKUPS:
            if self.verbose:
                print("Markup choice %s is not a known format.  Your notes probably won't look correct.  Acceptable "
                      "choices are: %s." % (options['markup'], get_markup_choices()))
            print("Markup error, aborting.")
            return
        if self.verbose:
            if not self.commit:
                print("This is only a dry-run, nothing will be saved.")
            print("Getting ready to process file: ", end='')
            print(self.file.name, end='')
            print(" into unit ", end='')
            print(self.unit_label.upper(), end='')
            print(" using markup: ", end='')
            print(MARKUPS[self.markup.lower()])
        self.process_file()
        if self.verbose:
            print("Closing file...")
        self.file.close()
        print("Done.")
