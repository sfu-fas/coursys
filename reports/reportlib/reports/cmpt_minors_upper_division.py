from ..report import Report
from ..queries import ActivePlanQuery, DB2_Query
import string


class GPASumByEmplidQuery(DB2_Query):
    query = string.Template("""
    SELECT DISTINCT
            emplid,
            SUM (UNT_EARNED) as credits_earned
      FROM
        (SELECT DISTINCT
            enrl.emplid,
            class.STRM,
            class.SUBJECT,
            class.CATALOG_NBR,
            enrl.UNT_EARNED
        FROM
            ps_stdnt_enrl enrl
        INNER JOIN
            ps_class_tbl class
            ON
            enrl.class_nbr = class.class_nbr
            AND enrl.strm = class.strm
          INNER JOIN PS_PERSONAL_DATA data on enrl.EMPLID = data.EMPLID
        WHERE
            enrl.earn_credit = 'Y'
            AND enrl.stdnt_enrl_status = 'E'
            AND class.class_type = 'E'
            AND class.subject = 'CMPT'
            AND enrl.UNITS_ATTEMPTED = 'Y'
            AND (class.catalog_nbr LIKE ' 3%' OR class.CATALOG_NBR LIKE ' 4%')
            AND enrl.crse_grade_input not in ('AU', 'W', 'WD', 'WE')
            AND data.EMPLID in $emplids)
      GROUP BY EMPLID;
      """)
    default_arguments = {'emplids': ['301008183']}


class CMPTMinorsUpperDivisionReport(Report):
    """
    Contact:  Brad Bart

    We are trying to determine which students are technically CMPT minors but using it as a
    path to take a CMPT major number of courses.  We want to know how many credits of UD CMPT courses they have
    already earned.
    """

    def run(self):
        student_query = ActivePlanQuery({'plans': ['CMPTMIN']})
        students = student_query.result()
        emplids = students.column_as_list('EMPLID')
        credits_earned = GPASumByEmplidQuery({'emplids': emplids})
        results = credits_earned.result()
        self.artifacts.append(results)
