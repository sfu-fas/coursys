from ..report import Report
from ..db2_query import DB2_Query
from coredata.models import Semester
import string


class GPAs_Query(DB2_Query):
    query = string.Template("""
        SELECT PLAN.ACAD_PLAN, TERM.CUM_GPA, PLANTBL.DESCR, PLANTBL.TRNSCR_DESCR
            FROM PS_ACAD_PROG PROG, PS_ACAD_PLAN PLAN, PS_STDNT_CAR_TERM TERM, PS_ACAD_PLAN_TBL AS PLANTBL
            WHERE PROG.EMPLID=PLAN.EMPLID AND PROG.ACAD_CAREER=PLAN.ACAD_CAREER AND PROG.STDNT_CAR_NBR=PLAN.STDNT_CAR_NBR AND PROG.EFFDT=PLAN.EFFDT AND PROG.EFFSEQ=PLAN.EFFSEQ
              AND PROG.EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PROG WHERE EMPLID=PROG.EMPLID AND ACAD_CAREER=PROG.ACAD_CAREER AND STDNT_CAR_NBR=PROG.STDNT_CAR_NBR AND EFFDT <= CURRENT DATE)
              AND PROG.EFFSEQ=(SELECT MAX(EFFSEQ) FROM PS_ACAD_PROG WHERE EMPLID=PROG.EMPLID AND ACAD_CAREER=PROG.ACAD_CAREER AND STDNT_CAR_NBR=PROG.STDNT_CAR_NBR AND EFFDT=PROG.EFFDT)
              AND PROG.PROG_STATUS='AC'
              AND PLAN.ACAD_PLAN IN (SELECT ACAD_PLAN FROM PS_ACAD_PLAN_TBL WHERE EFF_STATUS='A' AND ACAD_PLAN IN
                (SELECT DISTINCT ACAD_PLAN FROM PS_ACAD_PLAN_OWNER WHERE ACAD_ORG=$acad_org))
              AND PROG.EMPLID=TERM.EMPLID AND TERM.UNT_TAKEN_PRGRSS>0 AND TERM.STRM IN $strms
              AND PLANTBL.ACAD_PLAN=PLAN.ACAD_PLAN
              AND PLANTBL.EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PLAN_TBL WHERE ACAD_PLAN=PLANTBL.ACAD_PLAN AND EFF_STATUS='A' AND EFFDT<=CURRENT DATE)
              AND PROG.PROG_STATUS='AC' AND PLANTBL.EFF_STATUS='A'
              AND TERM.TOT_TAKEN_GPA>15 AND TERM.WITHDRAW_CODE='NWD'
              AND TERM.STRM=(SELECT MAX(STRM) FROM PS_STDNT_CAR_TERM WHERE EMPLID=PROG.EMPLID)
            ORDER BY PROG.EMPLID, PLAN.PLAN_SEQUENCE
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
