from ..report import Report
from ..table import Table
from ..queries import ActivePlanQuery, DB2_Query, NameQuery
from coredata.models import Person
import string


class GPASumByEmplidQuery(DB2_Query):
    query = string.Template("""
    SELECT DISTINCT
            EMPLID,
            SUM (UNT_EARNED) AS CREDITS_EARNED
      FROM
        (SELECT DISTINCT
            ENRL.EMPLID,
            CLASS.STRM,
            CLASS.SUBJECT,
            CLASS.CATALOG_NBR,
            ENRL.UNT_EARNED
        FROM
            PS_STDNT_ENRL ENRL
        INNER JOIN
            PS_CLASS_TBL CLASS
            ON
            ENRL.CLASS_NBR = CLASS.CLASS_NBR
            AND ENRL.STRM = CLASS.STRM
          INNER JOIN PS_PERSONAL_DATA DATA ON ENRL.EMPLID = DATA.EMPLID
        WHERE
            ENRL.EARN_CREDIT = 'Y'
            AND ENRL.STDNT_ENRL_STATUS = 'E'
            AND CLASS.CLASS_TYPE = 'E'
            AND CLASS.SUBJECT = 'CMPT'
            AND ENRL.UNITS_ATTEMPTED = 'Y'
            AND (CLASS.CATALOG_NBR LIKE ' 3%' OR CLASS.CATALOG_NBR LIKE ' 4%')
            AND ENRL.CRSE_GRADE_INPUT NOT IN ('AU', 'W', 'WD', 'WE')
            AND DATA.EMPLID IN $emplids)
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
