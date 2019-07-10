import itertools

from reports.reportlib import Table
from ..report import Report
from ..semester import current_semester
from ..db2_query import DB2_Query
import string

class CSPlanQuery(DB2_Query):
    title = "Plans relevant to CS"

    query = string.Template("""
        SELECT plan.acad_plan, plan.trnscr_descr AS descr
        FROM ps_acad_plan_owner owner
            INNER JOIN ps_acad_plan_tbl plan
            ON owner.acad_plan=plan.acad_plan
        WHERE owner.acad_org=$acad_org
            AND plan.eff_status='A'
        ORDER BY plan.effdt
    """)
    default_arguments = {
        'acad_org': 'COMP SCI',
    }


class ProgramGenderQuery(DB2_Query):
    title = "Plan by gender and admit term"
    description = "Fetch a list of active students by academic plan"

    query = string.Template("""
        SELECT admit.admit_term, plan.acad_plan, personal.sex, COUNT(*) AS n
        FROM (  /* find admit_term for the career(s) */
                SELECT prog.emplid, prog.acad_career, prog.stdnt_car_nbr, min(prog.admit_term) AS admit_term
                FROM ps_acad_prog prog
                WHERE prog.prog_status = 'AC'
                GROUP BY prog.emplid, prog.acad_career, prog.stdnt_car_nbr
            ) admit
            INNER JOIN ps_acad_plan plan /* acad_plan at the start of that term */
                ON admit.emplid=plan.emplid AND admit.acad_career=plan.acad_career AND admit.stdnt_car_nbr=plan.stdnt_car_nbr
            INNER JOIN ps_personal_data personal /* attach gender */
                ON plan.emplid = personal.emplid
        WHERE plan.acad_plan in $plans
            AND admit.admit_term >= $first_strm
            AND admit.admit_term <= $last_strm
            AND plan.effdt = (
                    SELECT MAX(temp_plan.effdt) 
                    FROM ps_acad_plan temp_plan
                    WHERE plan.emplid = temp_plan.emplid AND
                          plan.acad_career = temp_plan.acad_career AND 
                          plan.acad_plan = temp_plan.acad_plan AND
                          temp_plan.effdt < CURRENT DATE)
            AND plan.effseq = (
                    SELECT MAX(temp_plan_2.effseq)
                    FROM ps_acad_plan temp_plan_2
                    WHERE plan.emplid = temp_plan_2.emplid AND
                          plan.acad_career = temp_plan_2.acad_career AND 
                          plan.acad_plan = temp_plan_2.acad_plan AND
                          plan.effdt = temp_plan_2.effdt)
        GROUP BY admit.admit_term, plan.acad_plan, personal.sex
    """)
    default_arguments = {
        'first_strm': '1007',
        'last_strm': current_semester(),
        'plans': ['CMPTMAJ', 'CMPTMIN'],
        }


PLAN_CATEGORY = {
    'CCMPT': 'Minor/Cert',
    'CMPINSYJMA': 'Joint Maj',
    'CMPTBUSJMA': 'Joint Maj',
    'CMPTHON': 'Honours',
    'CMPTJHO': 'Honours',
    'CMPTJMA': 'Joint Maj',
    'CMPTMAJ': 'Major',
    'CMPTMATHJH': 'Honours',
    'CMPTMBBJMA': 'Joint Maj',
    'CMPTMIN': 'Minor/Cert',
    'CMPTMSC': 'MSc',
    'CMPTMSCZU': 'MSc',
    'CMPTPHD': 'PhD',
    'CMPTPHDZU': 'PhD',
    'CPMBD': 'MSc',
    'CPMCW': 'MSc',
    'GISHON': 'Honours',
    'GISMAJ': 'Joint Maj',
    'SOSYMAJ': 'Major',
    'ZUSFU': 'DDP',
}
CATEGORIES = [
    'Major',
    'Joint Maj',
    'Honours',
    'Minor/Cert',
    'DDP',
    'MSc',
    'PhD',
]
assert set(PLAN_CATEGORY.values()) == set(CATEGORIES)


def to_acad_year(row):
    strm = row['ADMIT_TERM']
    year = int(strm[:3]) + 1900
    sem = int(strm[-1]) # 1, 4, or 7

    if sem in [1,4]:
        return '%s/%s' % (year-1, year)
    else:
        return '%s/%s' % (year, year+1)


def to_cell(pr):
    f, t = pr
    res = '%i/%i' % (f, t)
    if t != 0:
        res += ' (%.0f%%)' % (f/t*100)
    return res


class CSGenderTableReport(Report):
    title = "CS Gender Table"
    description = "Summary of gender breakdown in differen CS-related programs, by year"

    def run(self):
        # all CS-related plans, for reference
        plans = CSPlanQuery()
        plan_dict = {}
        plan_table = plans.result()
        self.artifacts.append(plan_table)
        for acad_plan, descr in plan_table.rows:
            plan_dict[acad_plan] = descr

        # acad_plan -> category table, to join on our side
        category_table = Table()
        category_table.append_column('ACAD_PLAN')
        category_table.append_column('CATEGORY')
        for row in PLAN_CATEGORY.items():
            category_table.append_row(row)

        # actual data query
        by_gender = ProgramGenderQuery({'plans': list(PLAN_CATEGORY.keys())})
        by_gender_table = by_gender.result()
        by_gender_table.left_join(category_table, 'ACAD_PLAN')
        by_gender_table.compute_column('ACAD_YEAR', to_acad_year)

        by_gender_result = Table()
        by_gender_result.append_column('CATEGORY')
        by_gender_result.append_column('ACAD_YEAR')
        by_gender_result.append_column('GENDER')
        by_gender_result.append_column('COUNT')
        rows = list(by_gender_table.row_maps())
        rows.sort(key=lambda r: (r['ACAD_YEAR'], r['CATEGORY'], r['SEX']))

        for k, groups in itertools.groupby(rows, key=lambda r: (r['CATEGORY'], r['ACAD_YEAR'], r['SEX'])):
            count = sum(g['N'] for g in groups)
            row = list(k) + [count]
            by_gender_result.append_row(row)

        self.artifacts.append(by_gender_result)

        # pivot manually
        total = {}
        f_count = {}
        category_pos = {cat: i for i, cat in enumerate(CATEGORIES)}
        acad_years = sorted(set(by_gender_result.column_as_list('ACAD_YEAR')))
        for y in acad_years:
            total[y] = [0] * len(CATEGORIES)
            f_count[y] = [0] * len(CATEGORIES)

        for r in by_gender_result.row_maps():
            total[r['ACAD_YEAR']][category_pos[r['CATEGORY']]] += r['COUNT']
            if r['GENDER'] == 'F':
                f_count[r['ACAD_YEAR']][category_pos[r['CATEGORY']]] += r['COUNT']

        pivot = Table()
        pivot.append_column('YEAR')
        for c in CATEGORIES:
            pivot.append_column(c)

        for y in acad_years:
            row = [y]
            row.extend(map(to_cell, zip(f_count[y], total[y])))
            pivot.append_row(row)

        self.artifacts.append(pivot)
