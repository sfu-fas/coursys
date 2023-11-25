import gzip

from django.core.management.base import BaseCommand
from coredata.models import EnrolmentHistory
import json


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('unit_slug', type=str, help='slug of the unit whose data we want')
        parser.add_argument('output_file', type=str, help='file to write with enrolment history data (.ndjson.gz)')

    def handle(self, *args, **options):
        unit_slug = options['unit_slug']
        output_file = options['output_file']
        ehs = EnrolmentHistory.objects \
            .filter(offering__owner__slug=unit_slug) \
            .select_related('offering', 'offering__semester') \
            .order_by('offering', 'date')
        with gzip.open(output_file, 'wt', encoding='utf-8') as outfile:
            for i, eh in enumerate(ehs):
                if i%1000 == 0:
                    print(i)
                data = {
                    'semester': eh.offering.semester.name,
                    'subject': eh.offering.subject,
                    'number': eh.offering.number,
                    'section': eh.offering.section,
                    'campus': eh.offering.campus,
                    'component': eh.offering.component,
                    'instr_mode': eh.offering.instr_mode,
                    'date': eh.date.isoformat(),
                    'enrl_cap': eh.enrl_cap,
                    'enrl_tot': eh.enrl_tot,
                    'wait_tot': eh.wait_tot,
                }
                outfile.write(json.dumps(data))
                outfile.write('\n')