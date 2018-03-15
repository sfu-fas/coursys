from reports.reportlib.report import Report
from reports.reportlib.semester import registration_semester
from ..db2_query import DB2_Query
from ..queries import NameQuery, EmailQuery
import string


class WaitingListQuery(DB2_Query):
    title = "Waiting List Query"
    description = "Everyone enrolled as Waitlisted"

    query = string.Template("""
    SELECT e.emplid, e.ACAD_PROG, e.ENRL_STATUS_REASON, c.subject, c.catalog_nbr, c.CLASS_SECTION, c.descr, e.STATUS_DT
                 FROM ps_stdnt_enrl e
                 JOIN ps_class_tbl c
                   ON e.class_nbr=c.class_nbr AND e.strm=c.strm
                 AND c.class_type='E' AND e.stdnt_enrl_status='W'
                 AND e.strm=$strm AND c.SUBJECT=$subject 
                 ORDER BY e.strm, c.subject, c.catalog_nbr, e.STATUS_DT, e.emplid;
    """)


class ACADPlanQuery(DB2_Query):
    title = "ACAD Plan Query"
    description = "People's ACAD PLAN(s) given a specific semester and list of emplids"

    query = string.Template("""
    SELECT plan.emplid, plan.acad_plan from
        ps_acad_plan plan, ps_term_tbl trm
        WHERE effdt=(SELECT MAX(effdt) FROM ps_acad_plan WHERE emplid=plan.emplid AND effdt<=trm.term_begin_dt)
        AND effseq=(SELECT MAX(effseq) FROM ps_acad_plan WHERE emplid=plan.emplid AND effdt=plan.effdt)
        AND trm.strm=$strm AND plan.emplid IN $emplids;
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
