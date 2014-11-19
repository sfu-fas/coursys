from ..report import Report
from ..queries.fas_programs import get_fas_programs
from ..db2_query import DB2_Query
from coredata.models import Semester
import string



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

class InternationalGPAReport(Report):
    title = "GPA for FAS students with visa/citizenship"
    description = "GPA for FAS students with visa/citizenship"

    def run(self):
        current_semester = Semester.current()
        cmpt_progs, eng_progs = get_fas_programs()
        fas_progs = cmpt_progs + eng_progs

        students = InternationalGPAQuery({
            'acad_progs': fas_progs,
            'strm': current_semester.name,
        }).result()
        self.artifacts.append(students)