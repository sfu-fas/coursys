from reports.reportlib.report import Report
from reports.reportlib.semester import registration_semester
from ..db2_query import DB2_Query
from ..queries import NameQuery, EmailQuery
import string


class WaitingListQuery(DB2_Query):
    title = "Waiting List Query"
    description = "Everyone enrolled as Waitlisted"

    query = string.Template("""
    SELECT E.EMPLID, E.ACAD_PROG, C.SUBJECT, C.CATALOG_NBR, C.CLASS_SECTION, C.CLASS_NBR, E.STATUS_DT, E.STDNT_POSITIN
                 FROM PS_STDNT_ENRL E
                 JOIN PS_CLASS_TBL C
                   ON E.CLASS_NBR=C.CLASS_NBR AND E.STRM=C.STRM
                 AND C.CLASS_TYPE='E' AND E.STDNT_ENRL_STATUS='W'
                 AND E.STRM=$strm AND C.SUBJECT=$subject 
                 ORDER BY E.STRM, C.SUBJECT, C.CATALOG_NBR, E.STDNT_POSITIN, E.STATUS_DT, E.EMPLID;
    """)


class ACADPlanQuery(DB2_Query):
    title = "ACAD Plan Query"
    description = "People's ACAD PLAN(s) given a specific semester and list of emplids"

    query = string.Template("""
    SELECT PLAN.EMPLID, PLAN.ACAD_PLAN FROM
        PS_ACAD_PLAN PLAN, PS_TERM_TBL TRM
        WHERE EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PLAN WHERE EMPLID=PLAN.EMPLID AND EFFDT<=TRM.TERM_BEGIN_DT)
        AND EFFSEQ=(SELECT MAX(EFFSEQ) FROM PS_ACAD_PLAN WHERE EMPLID=PLAN.EMPLID AND EFFDT=PLAN.EFFDT)
        AND TRM.STRM=$strm AND PLAN.EMPLID IN $emplids;
    """)


class CMPTWaitingListReport(Report):
    title = "CMPT Waiting List"
    description = "This shows us everyone presently on a waitlist for a CMPT course for the appropriate " \
                  "registration semester, along with some other data about them"

    def run(self):
        strm = registration_semester()
        waitlist = WaitingListQuery({'strm': strm, 'subject': 'CMPT'})
        waitlist_students = waitlist.result()

        emplids = waitlist_students.column_as_list('EMPLID')
        emplid_list = list(set(emplids))

        acad_plans = ACADPlanQuery({'strm': strm, 'emplids': emplid_list})
        acad_plans_students = acad_plans.result()
        acad_plans_students.flatten('EMPLID')

        waitlist_students.left_join(acad_plans_students, 'EMPLID')

        # These are cached queries, so it shouldn't be *too* expensive to run them.
        # see bad_first_semester.py

        email_query = EmailQuery()
        email = email_query.result()
        email.filter(EmailQuery.campus_email)

        name_query = NameQuery()
        names = name_query.result()

        waitlist_students.left_join(names, "EMPLID")
        waitlist_students.left_join(email, "EMPLID")
        waitlist_students.remove_column("PREF_EMAIL_FLAG")
        waitlist_students.remove_column("E_ADDR_TYPE")

        self.artifacts.append(waitlist_students)
