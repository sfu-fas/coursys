"""
Queries about student progress
"""

from ..db2_query import DB2_Query
import string
from advisornotes.models import AdvisorVisit, AdvisorNote
from django.db.models import Count

from ..query import LocalDBQuery

class AdvisorVisits(LocalDBQuery):
    field_map = {
        'student__emplid': 'EMPLID_int',
        'student__count': 'Advisor Visits',
    }

    def __init__(self, unit_slugs, *args, **kwargs):
        super(AdvisorVisits, self).__init__(*args, **kwargs)
        self.query_values = AdvisorVisit.objects.filter(unit__slug__in=unit_slugs).values('student__emplid').annotate(Count('student'))

    def post_process(self):
        self.results_table.compute_column('EMPLID', lambda x: str(x["EMPLID_int"]))
        self.results_table.remove_column('EMPLID_int')

class AdvisorNotes(LocalDBQuery):
    field_map = {
        'student__emplid': 'EMPLID_int',
        'student__count': 'Advisor Notes',
    }

    def __init__(self, unit_slugs, *args, **kwargs):
        super(AdvisorNotes, self).__init__(*args, **kwargs)
        self.query_values = AdvisorNote.objects.filter(unit__slug__in=unit_slugs).exclude(hidden=True).values('student__emplid').annotate(Count('student'))

    def post_process(self):
        self.results_table.compute_column('EMPLID', lambda x: str(x["EMPLID_int"]))
        self.results_table.remove_column('EMPLID_int')


class InternationalGPAQuery(DB2_Query):
    query = string.Template("""
        SELECT term.emplid, term.acad_prog_primary, term.cum_gpa, stnd.acad_stndng_actn, c.descrshort AS citizen, vtbl.descrshort AS visa
        FROM ps_stdnt_car_term term
           JOIN (SELECT emplid, max(strm) strm FROM ps_acad_stdng_actn GROUP BY emplid) AS stnd_strm ON stnd_strm.emplid=term.emplid
           JOIN ps_acad_stdng_actn stnd ON stnd_strm.strm=stnd.strm AND stnd.emplid=term.emplid
           JOIN ps_citizenship cit ON cit.emplid=term.emplid
           JOIN ps_country_tbl c ON cit.country=c.country
           JOIN ps_visa_pmt_data v ON v.emplid=term.emplid AND v.effdt=(SELECT MAX(effdt) FROM ps_visa_pmt_data WHERE emplid=term.emplid AND effdt<=current date)
           JOIN ps_visa_permit_tbl vtbl ON v.visa_permit_type=vtbl.visa_permit_type
        WHERE
            term.strm = $strm
            AND term.tot_taken_gpa > 15
            AND term.unt_taken_prgrss > 0
            AND term.acad_prog_primary IN $acad_progs
            AND term.withdraw_code='NWD'
        ORDER BY term.emplid
    """)

    default_arguments = {
        'acad_progs': ['CMPT', 'CMPT2'],
        'strm': '1147',
        }


