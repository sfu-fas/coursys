from ..report import Report
from ..table import Table
from ..queries import ActivePlanQuery, DB2_Query, NameQuery
from coredata.models import Person
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


def get_userids_from_emplids(emplids):
    userids = Table()
    userids.append_column('EMPLID')
    userids.append_column('USERID')
    for e in emplids:
        userid = ''
        try:
            p = Person.objects.get(emplid=e)
        except Person.DoesNotExist:
            p = None
        if p:
            userid = p.userid or ''
        userids.append_row([e, userid])
    return userids


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
        name_query = NameQuery()
        names = name_query.result()
        results.left_join(names, 'EMPLID')
        userids = get_userids_from_emplids(emplids)
        results.left_join(userids, 'EMPLID')
        self.artifacts.append(results)
