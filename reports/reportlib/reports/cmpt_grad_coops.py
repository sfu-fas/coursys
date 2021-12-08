from ..report import Report
from ..queries import SingleCourseStrmQuery, NameQuery
from ..db2_query import DB2_Query
import string


class CMPTGradCoopQuery(DB2_Query):
    """
    We need to do our own query here.  It's the SingleCourseStrmQuery, but customized for multiple courses.
    We can't easily just do a Multiple Course one with an IN for the course number, since those are strings with
    a lot of padding.  Instead we have to do multiple ORs with LIKE statements.
    """
    title = "CMPT Grad Coop Query"
    description = "All students who have taken any of CMPT 626, 627, 628."
    query = string.Template("""
        SELECT DISTINCT
            ENRL.EMPLID,
            CLASS.STRM,
            CLASS.SUBJECT,
            CLASS.CATALOG_NBR
        FROM
            PS_STDNT_ENRL ENRL
        INNER JOIN
            PS_CLASS_TBL CLASS
            ON
            ENRL.CLASS_NBR = CLASS.CLASS_NBR
            AND ENRL.STRM = CLASS.STRM
        WHERE
            ENRL.EARN_CREDIT = 'Y'
            AND ENRL.STDNT_ENRL_STATUS = 'E'
            AND CLASS.CLASS_TYPE = 'E'
            AND CLASS.SUBJECT = 'CMPT'
            AND (CLASS.CATALOG_NBR LIKE '%626%' OR CLASS.CATALOG_NBR LIKE '%627%' OR CLASS.CATALOG_NBR LIKE '%628%')
            AND ENRL.CRSE_GRADE_INPUT NOT IN ('AU', 'W', 'WD', 'WE')
        ORDER BY
            ENRL.EMPLID
            """)
    exclude_list = ['AU', 'W', 'WD', 'WE']


class CMPTGradCoopReport(Report):
    """
    Contact: Tracy Bruneau

    Here we are gathering all CMPT Grad students who have taken CMPT Co-Op courses, and when they did so.
    """

    title = "CMPT Grad Co-Op"
    description = "Everyone who has taken the CMPT Grad Co-Op classes, and when they did so."

    def run(self):
        grad_coop_query = CMPTGradCoopQuery()
        grad_coop_students = grad_coop_query.result()
        name_query = NameQuery()
        names = name_query.result()

        grad_coop_students.left_join(names, "EMPLID")

        self.artifacts.append(grad_coop_students)
