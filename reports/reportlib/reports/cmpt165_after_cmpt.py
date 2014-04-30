from reports.reportlib.report import Report
from reports.reportlib.table import Table
from reports.reportlib.semester import current_semester
from ..queries.personal_query import EmailQuery, NameQuery
from ..db2_query import DB2_Query
import string, itertools, collections


class CMPT165_after_CMPT_Query(DB2_Query):
    title = "Students taking CMPT 165 after a CMPT >=200 course"
    description = "Students taking CMPT 165 after a 200-or-above CMPT course."

    query = string.Template("""
        SELECT se.emplid, ct.strm, ct.subject, ct.catalog_nbr, ct.class_section, se.crse_grade_off
        FROM ps_class_tbl ct
          INNER JOIN ps_stdnt_enrl se ON ct.class_nbr=se.class_nbr and ct.strm=se.strm and se.enrl_status_reason IN ('ENRL','EWAT')
        WHERE
          ct.strm<='$strm' AND ct.subject='CMPT'
          AND (ct.catalog_nbr LIKE ' 2%' OR ct.catalog_nbr LIKE ' 3%' OR ct.catalog_nbr LIKE ' 4%')
          AND ct.class_type='E'
          AND se.emplid in (SELECT se.emplid FROM ps_class_tbl ct
            INNER JOIN ps_stdnt_enrl se ON ct.class_nbr=se.class_nbr and ct.strm=se.strm and se.enrl_status_reason IN ('ENRL','EWAT')
            WHERE ct.strm>='1141' AND ct.subject='CMPT' AND ct.catalog_nbr LIKE '%165%')
          ORDER BY se.emplid, ct.strm, ct.subject, ct.catalog_nbr
    """)



class CMPT165_after_CMPT_Report(Report):
    title = "Students taking CMPT 165 after a CMPT >=200 course"
    description = "Students taking CMPT 165 after a 200-or-above CMPT course."

    def run(self):
        semester = current_semester()
        taking_165_query = CMPT165_after_CMPT_Query({'strm': semester})
        taking_165 = taking_165_query.result()

        email = EmailQuery().result()
        email.filter(EmailQuery.campus_email)
        email.remove_column("PREF_EMAIL_FLAG")
        email.remove_column("E_ADDR_TYPE")
        taking_165.left_join(email, "EMPLID")

        names = NameQuery().result()
        taking_165.left_join(names, "EMPLID")

        self.artifacts.append(taking_165)


