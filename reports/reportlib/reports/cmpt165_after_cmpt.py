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
        SELECT SE.EMPLID, CT.STRM, CT.SUBJECT, CT.CATALOG_NBR, CT.CLASS_SECTION, SE.CRSE_GRADE_OFF
        FROM PS_CLASS_TBL CT
          INNER JOIN PS_STDNT_ENRL SE ON CT.CLASS_NBR=SE.CLASS_NBR AND CT.STRM=SE.STRM AND SE.ENRL_STATUS_REASON IN ('ENRL','EWAT')
        WHERE
          CT.STRM<='$strm' AND CT.SUBJECT='CMPT'
          AND (CT.CATALOG_NBR LIKE ' 2%' OR CT.CATALOG_NBR LIKE ' 3%' OR CT.CATALOG_NBR LIKE ' 4%' OR CT.CATALOG_NBR LIKE '%125%' OR CT.CATALOG_NBR LIKE '%135%')
          AND CT.CLASS_TYPE='E'
          AND SE.EMPLID IN (SELECT SE.EMPLID FROM PS_CLASS_TBL CT
            INNER JOIN PS_STDNT_ENRL SE ON CT.CLASS_NBR=SE.CLASS_NBR AND CT.STRM=SE.STRM AND SE.ENRL_STATUS_REASON IN ('ENRL','EWAT')
            WHERE CT.STRM=$strm AND CT.SUBJECT='CMPT' AND CT.CATALOG_NBR LIKE '%165%')
          ORDER BY SE.EMPLID, CT.STRM, CT.SUBJECT, CT.CATALOG_NBR
    """)
    default_arguments = {
        'strm': current_semester()
        }




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


