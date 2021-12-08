from reports.reportlib.report import Report
from reports.reportlib.table import Table
from reports.reportlib.semester import current_semester
from ..db2_query import DB2_Query
import string, itertools, collections


class PlansInCoursesQuery(DB2_Query):
    title = "All academic plans for students in CMPT courses"
    description = "All academic plans for students in courses, as of the start of the semester"

    query = string.Template("""
    SELECT CLS.SUBJECT, CLS.CATALOG_NBR, CLS.CLASS_SECTION, CLS.CAMPUS, STD.EMPLID, CLS.ENRL_TOT, CLS.ENRL_CAP, APLAN.ACAD_PLAN
    FROM PS_CLASS_TBL CLS
      INNER JOIN PS_STDNT_ENRL STD
        ON STD.CLASS_NBR=CLS.CLASS_NBR
          AND STD.STRM=CLS.STRM
          AND STD.ENRL_STATUS_REASON IN ('ENRL','EWAT')
      INNER JOIN PS_TERM_TBL TRM
        ON CLS.STRM=TRM.STRM AND TRM.ACAD_CAREER='UGRD'
      INNER JOIN PS_ACAD_PLAN APLAN
        ON APLAN.EMPLID=STD.EMPLID
          AND EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PLAN WHERE EMPLID=APLAN.EMPLID AND EFFDT<=TRM.TERM_BEGIN_DT)
          AND EFFSEQ=(SELECT MAX(EFFSEQ) FROM PS_ACAD_PLAN WHERE EMPLID=APLAN.EMPLID AND EFFDT=APLAN.EFFDT)
    WHERE
      CLS.CLASS_SECTION LIKE '%00'
      AND CLS.CANCEL_DT IS NULL
      AND CLS.ACAD_ORG='COMP SCI'
      AND CLS.STRM=$strm
    ORDER BY CLS.SUBJECT ASC, CLS.CATALOG_NBR ASC, CLS.CLASS_SECTION ASC, STD.EMPLID ASC, APLAN.ACAD_PLAN ASC""")


class PlansDescriptionQuery(DB2_Query):
    title = "Descriptions of academic plans"
    description = "Descriptions of academic plans we care about here"

    query = string.Template("""SELECT acad_plan, trnscr_descr
               FROM PS_ACAD_PLAN_TBL APT
               WHERE EFF_STATUS='A' AND ACAD_PLAN IN $plans
               AND EFFDT=(SELECT MAX(EFFDT) FROM PS_ACAD_PLAN_TBL WHERE ACAD_PLAN=APT.ACAD_PLAN)
               ORDER BY ACAD_PLAN""")


def _rowkey(row):
    "key for counting programs in each offering"
    return (row['SUBJECT'], row['CATALOG_NBR'], row['CLASS_SECTION'],  row['CAMPUS'], row['ENRL_TOT'], row['ENRL_CAP'])

def counter(iter):
    """
    Fake collections.Counts, since we don't have that in Python 2.6 on production
    """
    counts = {}
    for o in iter:
        counts[o] = counts.get(o, 0) + 1
    return counts

#counter = collections.Counter

class MajorsInCoursesReport(Report):
    title = "Majors in courses"
    description = "This report summarizes the academic programs of students in each CMPT course."

    def run(self):
        semester = current_semester()

        # Get the full list of plans in each offering
        plans_query = PlansInCoursesQuery({'strm': semester})
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
        for (subj, nbr, sect, campus, tot, cap), plans in offering_plans:
            plans = list(plans)
            found_plans |= set(plans)
            count = counter(plans)
            count = [(n,plan) for plan,n in count.items()]
            count.sort()
            count.reverse()
            count_str = ', '.join("%i*%s" % (n,plan) for n,plan in count)
            programs.append_row(("%04i"%(semester), subj, nbr, sect, campus, tot, cap, count_str))

        self.artifacts.append(programs)

        # get a cheat-sheet of the plan codes
        found_plans = list(found_plans)
        found_plans.sort()
        descr = PlansDescriptionQuery({'plans': found_plans}).result()
        self.artifacts.append(descr)


