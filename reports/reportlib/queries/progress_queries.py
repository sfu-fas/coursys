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
        SELECT TERM.EMPLID, TERM.ACAD_PROG_PRIMARY, TERM.CUM_GPA, STND.ACAD_STNDNG_ACTN, C.DESCRSHORT AS CITIZEN, VTBL.DESCRSHORT AS VISA
        FROM PS_STDNT_CAR_TERM TERM
           JOIN (SELECT EMPLID, MAX(STRM) STRM FROM PS_ACAD_STDNG_ACTN GROUP BY EMPLID) AS STND_STRM ON STND_STRM.EMPLID=TERM.EMPLID
           JOIN PS_ACAD_STDNG_ACTN STND ON STND_STRM.STRM=STND.STRM AND STND.EMPLID=TERM.EMPLID
           JOIN PS_CITIZENSHIP CIT ON CIT.EMPLID=TERM.EMPLID
           JOIN PS_COUNTRY_TBL C ON CIT.COUNTRY=C.COUNTRY
           LEFT JOIN PS_VISA_PMT_DATA V ON V.EMPLID=TERM.EMPLID
           LEFT JOIN PS_VISA_PERMIT_TBL VTBL ON V.VISA_PERMIT_TYPE=VTBL.VISA_PERMIT_TYPE
        WHERE
            TERM.STRM = $strm
            AND (V.EFFDT IS NULL OR V.EFFDT=(SELECT MAX(EFFDT) FROM PS_VISA_PMT_DATA WHERE EMPLID=TERM.EMPLID AND EFFDT<=CURRENT DATE))
            AND TERM.TOT_TAKEN_GPA > 15
            AND TERM.UNT_TAKEN_PRGRSS > 0
            AND TERM.ACAD_PROG_PRIMARY IN $acad_progs
            AND TERM.WITHDRAW_CODE='NWD'
        ORDER BY TERM.EMPLID
    """)

    default_arguments = {
        'acad_progs': ['CMPT', 'CMPT2'],
        'strm': '1147',
        }


