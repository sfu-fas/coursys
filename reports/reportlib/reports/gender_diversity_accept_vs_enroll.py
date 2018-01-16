from reports.reportlib.report import Report
from reports.reportlib.table import Table
from reports.reportlib.semester import current_semester, semester_range, Semester
from ..db2_query import DB2_Query
import string

class AcceptedQuery(DB2_Query):
    title = "Accepted Students and Genders"
    description = "The list of students we accepted in specific plans who start next semester, and their gender."

    query = string.Template("""
    SELECT pers.emplid, pers.sex, c.descrshort AS citizen
      FROM PS_PERSONAL_DATA pers
        JOIN ps_citizenship cit ON cit.emplid=pers.emplid
        JOIN ps_country_tbl c ON cit.country=c.country
    WHERE
      pers.emplid IN
      (SELECT DISTINCT (plan.EMPLID) from PS_ACAD_PLAN plan where REQ_TERM=$strm AND ACAD_PLAN IN $acad_plans);
                            """)

    plans_list = ['CMPTMAJ','DCMPT','CMPTMIN','CMPTHON','CMPTJMA','CMPTJHO','SOSYMAJ','ZUSFU']

    default_arguments = {'strm': current_semester().increment(1), 'acad_plans': plans_list}

    def __init__(self, query_args):
        for arg in list(AcceptedQuery.default_arguments.keys()):
            if arg not in query_args:
                query_args[arg] = AcceptedQuery.default_arguments[arg]
        self.title = "Accepted Students and Genders - " + Semester(query_args["strm"]).long_form()
        super(AcceptedQuery, self).__init__(query_args)

class EnrolledQuery(DB2_Query):
    title = "Enrolled Students and Genders"
    description = "The list of students enrolled in specific programs who start next semester, and their gender."

    query = string.Template("""
    SELECT pers.emplid, pers.sex, c.descrshort AS citizentest
    FROM PS_PERSONAL_DATA pers
      JOIN ps_citizenship cit ON cit.emplid=pers.emplid
      JOIN ps_country_tbl c ON cit.country=c.country
    WHERE pers.EMPLID IN (SELECT
    DISTINCT (EMPLID) from PS_ACAD_PROG
    WHERE REQ_TERM=$strm AND PROG_STATUS='AC' AND PROG_ACTION='MATR' AND ACAD_PROG in $acad_progs );
    """)

    progs_list = ['CMPT', 'CMPT2']
    default_arguments = {'strm': str(current_semester().increment(1)), 'acad_progrs': progs_list}

    def __init__(self, query_args):
        for arg in list(EnrolledQuery.default_arguments.keys()):
            if arg not in query_args:
                query_args[arg] = EnrolledQuery.default_arguments[arg]
        self.title = "Enrolled Students and Genders - " + Semester(query_args["strm"]).long_form()
        super(EnrolledQuery, self).__init__(query_args)

class GenderDiversityAcceptvsEnrollReport(Report):
    title = "Gender Diversity Accepted vs Enrolled"
    description = "We are trying to see the gender diversity of the students we have accepted vs the students who " \
                  "actually enrolled."

    def run(self):
        AcceptedStudentsQuery = AcceptedQuery({'strm': str(current_semester().increment(1)), 'acad_plans':
                                               ['CMPTMAJ', 'DCMPT', 'CMPTMIN', 'CMPTHON', 'CMPTJMA', 'CMPTJHO',
                                                'SOSYMAJ', 'ZUSFU']})
        AcceptedStudents = AcceptedStudentsQuery.result()
        EnrolledStudentsQuery = EnrolledQuery({'strm': str(current_semester().increment(1)), 'acad_progs':
                                               ['CMPT', 'CMPT2']})
        EnrolledStudents = EnrolledStudentsQuery.result()

        # Let's calculate our totals so we can display those numbers as well.
        accepted_list = AcceptedStudents.column_as_list("SEX")
        accepted_total = len(accepted_list)
        accepted_m_count = len([i for i in accepted_list if i=='M'])
        accepted_f_count = len([i for i in accepted_list if i=='F'])
        accepted_u_count = len([i for i in accepted_list if i=='U'])

        enrolled_list = EnrolledStudents.column_as_list("SEX")
        enrolled_total = len(enrolled_list)
        enrolled_m_count = len([i for i in enrolled_list if i == 'M'])
        enrolled_f_count = len([i for i in enrolled_list if i == 'F'])
        enrolled_u_count = len([i for i in enrolled_list if i == 'U'])

        # Let's create two new tables to display these results.
        accepted_totals = Table()
        accepted_totals.append_column('TOTAL_COUNT')
        accepted_totals.append_column('M_COUNT')
        accepted_totals.append_column('M_PERCENT')
        accepted_totals.append_column('F_TOTAL')
        accepted_totals.append_column('F_PERCENT')
        accepted_totals.append_column('U_COUNT')
        accepted_totals.append_column('U_PERCENT')
        accepted_totals.append_row([accepted_total, accepted_m_count, 100.0 * accepted_m_count/accepted_total,
                                   accepted_f_count, 100.0 * accepted_f_count/accepted_total, accepted_u_count, 
                                   100.0 * accepted_u_count/accepted_total])

        enrolled_totals = Table()
        enrolled_totals.append_column('TOTAL_COUNT')
        enrolled_totals.append_column('M_COUNT')
        enrolled_totals.append_column('M_PERCENT')
        enrolled_totals.append_column('F_TOTAL')
        enrolled_totals.append_column('F_PERCENT')
        enrolled_totals.append_column('U_COUNT')
        enrolled_totals.append_column('U_PERCENT')
        enrolled_totals.append_row([enrolled_total, enrolled_m_count, 100.0 * enrolled_m_count / enrolled_total,
                                   enrolled_f_count, 100.0 * enrolled_f_count / enrolled_total, enrolled_u_count,
                                   100.0 * enrolled_u_count / enrolled_total])

        self.artifacts.append(AcceptedStudents)
        self.artifacts.append(accepted_totals)
        self.artifacts.append(EnrolledStudents)
        self.artifacts.append(enrolled_totals)
