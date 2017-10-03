from ..report import Report
from ..db2_query import DB2_Query
from coredata.models import Semester
import string


class GPAs_Query(DB2_Query):
    query = string.Template("""
        SELECT plan.acad_plan, term.cum_gpa
            FROM ps_acad_prog prog, ps_acad_plan plan, ps_stdnt_car_term term
            WHERE prog.emplid=plan.emplid AND prog.acad_career=plan.acad_career AND prog.stdnt_car_nbr=plan.stdnt_car_nbr AND prog.effdt=plan.effdt AND prog.effseq=plan.effseq
              AND prog.effdt=(SELECT MAX(effdt) FROM ps_acad_prog WHERE emplid=prog.emplid AND acad_career=prog.acad_career AND stdnt_car_nbr=prog.stdnt_car_nbr AND effdt <= current date)
              AND prog.effseq=(SELECT MAX(effseq) FROM ps_acad_prog WHERE emplid=prog.emplid AND acad_career=prog.acad_career AND stdnt_car_nbr=prog.stdnt_car_nbr AND effdt=prog.effdt)
              AND prog.prog_status='AC'
              AND plan.acad_plan IN (SELECT acad_plan FROM ps_acad_plan_tbl WHERE eff_status='A' AND acad_plan IN
                (SELECT DISTINCT acad_plan FROM ps_acad_plan_owner WHERE acad_org=$acad_org))
              AND prog.emplid=term.emplid AND term.unt_taken_prgrss>0 AND term.strm in $strms
              AND term.tot_taken_gpa>15 AND term.withdraw_code='NWD'
              AND term.strm=(SELECT MAX(strm) FROM ps_stdnt_car_term WHERE emplid=prog.emplid)
            ORDER BY prog.emplid, plan.plan_sequence
        """)

    default_arguments = {
        'strms': ['1171', '1174', '1177'],
        'acad_org': 'COMP SCI',
    }


class CMPTGPAs_Report(Report):
    title = "CS GPAs below/above continuation"
    description = "How many students have what GPAs in CS?"

    def run(self):
        current_semester = Semester.current()
        semesters = [current_semester.name, current_semester.offset_name(-1), current_semester.offset_name(-2)]
        gpas = GPAs_Query(query_args={'strms': semesters, 'acad_org': 'COMP SCI'})
        self.artifacts.append(gpas.result())
