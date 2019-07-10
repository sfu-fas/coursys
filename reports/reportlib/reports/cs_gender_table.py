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
        'first_strm': '1001',
        'last_strm': current_semester(),
        'plans': ['CMPTMAJ', 'CMPTMIN'],
        }


PLAN_CATEGORY = {
    'CCMPT': 'Certificate',
    'CMPINSYJMA': 'Joint Maj',
    'CMPTBUSJMA': 'Joint Maj',
    'CMPTHON': 'Honours',
    'CMPTJHO': 'Joint Hon',
    'CMPTJMA': 'Joint Maj',
    'CMPTMAJ': 'Major',
    'CMPTMATHJH': 'Joint Hon',
    'CMPTMBBJMA': 'Joint Maj',
    'CMPTMIN': 'Minor',
    'CMPTMSC': 'MSc',
    'CMPTMSCZU': 'MSc',
    'CMPTPHD': 'PhD',
    'CMPTPHDZU': 'PhD',
    'CPMBD': 'MSc',
    'CPMCW': 'MSc',
    'GISHON': 'Joint Hon',
    'GISMAJ': 'Joint Maj',
    'SOSYMAJ': 'Major',
    'ZUSFU': 'DDP',
}


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

        self.artifacts.append(by_gender_table)

        
