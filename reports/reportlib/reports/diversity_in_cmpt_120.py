from reports.reportlib.report import Report
from reports.reportlib.table import Table
from reports.reportlib.semester import current_semester, semester_range, Semester
from ..db2_query import DB2_Query
import string, itertools, collections


class PlansInCoursesQuery(DB2_Query):
    title = "All academic plans for students in CMPT courses"
    description = "All academic plans for students in courses, as of the start of the semester"

    query = string.Template("""
    SELECT cls.strm, cls.subject, cls.catalog_nbr, cls.class_section, cls.campus, std.emplid, cls.enrl_tot,
    cls.ENRL_CAP, plan.acad_plan, data.SEX
    FROM ps_class_tbl cls
      INNER JOIN ps_stdnt_enrl std
        ON std.class_nbr=cls.class_nbr
          AND std.strm=cls.strm
          AND std.enrl_status_reason IN ('ENRL','EWAT')
      INNER JOIN ps_term_tbl trm
        ON cls.strm=trm.strm AND trm.acad_career='UGRD'
      INNER JOIN ps_acad_plan plan
        ON plan.emplid=std.emplid
          AND effdt=(SELECT MAX(effdt) FROM ps_acad_plan WHERE emplid=plan.emplid AND effdt<=trm.term_begin_dt)
          AND effseq=(SELECT MAX(effseq) FROM ps_acad_plan WHERE emplid=plan.emplid AND effdt=plan.effdt)
       INNER JOIN PS_PERSONAL_DATA data on plan.EMPLID = data.EMPLID
    WHERE
      cls.class_section LIKE '%00'
      AND cls.cancel_dt IS NULL
      AND cls.acad_org='COMP SCI'
      AND cls.strm IN $strm
      AND cls.subject = 'CMPT'
      and cls.CATALOG_NBR LIKE '%120%'
    ORDER BY cls.strm, cls.subject ASC, cls.catalog_nbr ASC, cls.class_section ASC, std.emplid ASC, plan.acad_plan ASC""")


class PlansDescriptionQuery(DB2_Query):
    title = "Descriptions of academic plans"
    description = "Descriptions of academic plans we care about here"

    query = string.Template("""SELECT acad_plan, trnscr_descr
               FROM PS_ACAD_PLAN_TBL apt
               WHERE eff_status='A' AND acad_plan IN $plans
               AND effdt=(SELECT MAX(effdt) FROM PS_ACAD_PLAN_TBL WHERE acad_plan=apt.acad_plan)
               ORDER BY acad_plan""")


def _rowkey(row):
    "key for counting programs in each offering"
    return (row ['STRM'], row['SUBJECT'], row['CATALOG_NBR'], row['CLASS_SECTION'],  row['CAMPUS'], row['ENRL_TOT'],
            row['ENRL_CAP'], row['SEX'])

def counter(iter):
    """
    Fake collections.Counts, since we don't have that in Python 2.6 on production
    """
    counts = {}
    for o in iter:
        counts[o] = counts.get(o, 0) + 1
    return counts

#counter = collections.Counter


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
            count_str = ''

        for strm in count:
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

