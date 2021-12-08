from reports.reportlib.report import Report
from reports.reportlib.table import Table
from reports.reportlib.semester import current_semester, semester_range, Semester
from ..db2_query import DB2_Query
import string, itertools, collections


class PlansInCoursesQuery(DB2_Query):
    title = "All academic plans for students in CMPT courses"
    description = "All academic plans for students in courses, as of the start of the semester"

    query = string.Template("""
    SELECT CLS.STRM, CLS.SUBJECT, CLS.CATALOG_NBR, CLS.CLASS_SECTION, CLS.CAMPUS, STD.EMPLID, CLS.ENRL_TOT,
    CLS.ENRL_CAP, PLAN.ACAD_PLAN, DATA.SEX
    FROM PS_CLASS_TBL CLS
      INNER JOIN PS_STDNT_ENRL STD
        ON STD.CLASS_NBR=CLS.CLASS_NBR
          AND STD.STRM=CLS.STRM
          AND STD.ENRL_STATUS_REASON IN ('ENRL','EWAT')
      INNER JOIN PS_TERM_TBL TRM
        ON CLS.STRM=TRM.STRM AND TRM.ACAD_CAREER='UGRD'
      INNER JOIN PS_ACAD_PLAN PLAN
        ON PLAN.EMPLID=STD.EMPLID
          AND EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PLAN WHERE EMPLID=PLAN.EMPLID AND EFFDT<=TRM.TERM_BEGIN_DT)
          AND EFFSEQ=(SELECT MAX(EFFSEQ) FROM PS_ACAD_PLAN WHERE EMPLID=PLAN.EMPLID AND EFFDT=PLAN.EFFDT)
       INNER JOIN PS_PERSONAL_DATA DATA ON PLAN.EMPLID = DATA.EMPLID
    WHERE
      CLS.CLASS_SECTION LIKE '%00'
      AND CLS.CANCEL_DT IS NULL
      AND CLS.ACAD_ORG='COMP SCI'
      AND CLS.STRM IN $strm
      AND CLS.SUBJECT = 'CMPT'
      AND CLS.CATALOG_NBR LIKE '%120%'
    ORDER BY CLS.STRM, CLS.SUBJECT ASC, CLS.CATALOG_NBR ASC, CLS.CLASS_SECTION ASC, STD.EMPLID ASC, PLAN.ACAD_PLAN ASC""")


class PlansDescriptionQuery(DB2_Query):
    title = "Descriptions of academic plans"
    description = "Descriptions of academic plans we care about here"

    query = string.Template("""SELECT acad_plan, trnscr_descr
               FROM PS_ACAD_PLAN_TBL apt
               WHERE EFF_STATUS='A' AND ACAD_PLAN IN $plans
               AND EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PLAN_TBL WHERE ACAD_PLAN=APT.ACAD_PLAN)
               ORDER BY ACAD_PLAN""")


def _rowkey(row):
    "key for counting programs in each offering"
    return (row ['STRM'], row['SUBJECT'], row['CATALOG_NBR'], row['CLASS_SECTION'],  row['CAMPUS'], row['ENRL_TOT'],
            row['ENRL_CAP'], row['SEX'])


class DiversityInCMPT120Report(Report):
    title = "Diversity in CMPT 120"
    description = "This report summarizes the academic programs and genders of students in CMPT 120"

    def run(self):
        semesters = list(semester_range(Semester(1071), current_semester()))
        # Get the full list of plans in each offering
        plans_query = PlansInCoursesQuery({'strm': semesters})
        plans = plans_query.result()
        # create a table with the counts of plans, not individual student info
        programs = Table()
        programs.append_column('SEMESTER')
        programs.append_column('SUBJECT')
        programs.append_column('CATALOG_NBR')
        programs.append_column('CLASS_SECTION')
        programs.append_column('CAMPUS')
        programs.append_column('ENRL_TOTAL')
        programs.append_column('ENRL_CAP')
        programs.append_column('PLANS')

        # group plans by offering
        offering_plans = (
            (offering, (r['ACAD_PLAN'] for r in rows))
            for offering, rows
            in itertools.groupby(plans.row_maps(), _rowkey))

        # count for each offering
        found_plans = set()
        count = {}

        # Build an object to count the instance of each gender in each plan for each semester
        for (strm, subj, nbr, sect, campus, tot, cap, sex), plans in offering_plans:
            plans = list(plans)
            found_plans |= set(plans)
            # We want to count too many things, let's store it in an object:
            if strm not in count:
                count[strm] = {}
            current_strm = count.get(strm)
            for plan in plans:
                if plan not in current_strm:
                    current_strm[plan] = {}
                current_plan = current_strm[plan]
                current_plan['TOTAL'] = current_plan.get('TOTAL', 0) + 1
                if sex == 'M':
                    current_plan['M'] = current_plan.get('M', 0) + 1
                elif sex == 'F':
                    current_plan['F'] = current_plan.get('F', 0) +1

        # Let's iterate through our counter object and just add one row per semester, concatenating the string with
        # the breakdown of males/females in each plan.
        for strm in count:
            count_str = ''
            for plan in count[strm]:
                m_count = count[strm].get(plan).get('M', 0)
                f_count = count[strm].get(plan).get('F', 0)
                total_count = count[strm].get(plan).get('TOTAL', 0)
                count_str += str("%s Total: %i, M: %i, F: %i  " % (plan, total_count, m_count, f_count))
            programs.append_row((strm, subj, nbr, sect, campus, tot, cap, count_str))


        self.artifacts.append(programs)

        # get a cheat-sheet of the plan codes
        found_plans = list(found_plans)
        found_plans.sort()
        descr = PlansDescriptionQuery({'plans': found_plans}).result()
        self.artifacts.append(descr)

