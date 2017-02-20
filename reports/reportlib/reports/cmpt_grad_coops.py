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
            enrl.emplid,
            class.STRM,
            class.subject,
            class.catalog_nbr
        FROM
            ps_stdnt_enrl enrl
        INNER JOIN
            ps_class_tbl class
            ON
            enrl.class_nbr = class.class_nbr
            AND enrl.strm = class.strm
        WHERE
            enrl.earn_credit = 'Y'
            AND enrl.stdnt_enrl_status = 'E'
            AND class.class_type = 'E'
            AND class.subject = 'CMPT'
            AND (class.catalog_nbr LIKE '%626%' OR class.catalog_nbr LIKE '%627%' OR class.catalog_nbr LIKE '%628%')
            AND enrl.crse_grade_input not in ('AU', 'W', 'WD', 'WE')
        ORDER BY
            enrl.emplid
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
