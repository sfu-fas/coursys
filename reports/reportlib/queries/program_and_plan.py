from ..db2_query import DB2_Query
from ..table import Table
from ..semester import Semester, current_semester, registration_semester

import datetime
import copy
import string

class ActiveProgramQuery(DB2_Query):
    title = "Active Program Query"
    description = "Fetch a list of active students by academic program" 

    query = string.Template("""
    SELECT DISTINCT 
        prog.emplid,
        prog.acad_career,
        prog.acad_prog
    FROM 
        ps_acad_prog prog
    INNER JOIN
        ps_stdnt_car_term car_term 
        ON
        prog.emplid = car_term.emplid AND
        prog.acad_career = car_term.acad_career AND
        prog.stdnt_car_nbr = car_term.stdnt_car_nbr
    WHERE 
        prog.acad_prog IN $programs
        AND prog.prog_status = 'AC' 
        AND car_term.withdraw_code = 'NWD'
        AND car_term.strm < $registration_semester
        AND car_term.strm >= $third_prior_semester
        AND prog.effdt = (
            SELECT MAX(temp_prog.effdt) 
            FROM ps_acad_prog temp_prog
            WHERE prog.emplid = temp_prog.emplid AND
                  prog.acad_career = temp_prog.acad_career AND 
                  prog.acad_prog = temp_prog.acad_prog AND
                  temp_prog.effdt < $effective_date)
        AND prog.effseq = (
            SELECT MAX(temp_prog_2.effseq)
            FROM ps_acad_prog temp_prog_2
            WHERE prog.emplid = temp_prog_2.emplid AND
                  prog.acad_career = temp_prog_2.acad_career AND 
                  prog.acad_prog = temp_prog_2.acad_prog AND
                  prog.effdt = temp_prog_2.effdt)
        """)
    default_arguments = {
        'programs': ['CMPT'],
        'effective_date': datetime.datetime.now(), 
        'registration_semester': registration_semester(),
        'third_prior_semester': registration_semester().increment(-3)
        }


class ActivePlanQueryWithReqTerm(DB2_Query):

    title = "Active Plan Query With Requirement Term"
    description = "Fetch a list of active students by academic plan" 
    # This is likely to produce duplicates - students that are enrolled in more than one academic plan. 

    query = string.Template("""
    SELECT DISTINCT 
        plan.emplid,
        plan.acad_career,
        prog.acad_prog,
        plan.acad_plan,
        plan.req_term
    FROM 
        ps_acad_plan plan
    INNER JOIN
        ps_stdnt_car_term car_term 
        ON
        plan.emplid = car_term.emplid AND
        plan.acad_career = car_term.acad_career AND
        plan.stdnt_car_nbr = car_term.stdnt_car_nbr
    INNER JOIN 
        ps_acad_prog prog
        ON
        plan.emplid = prog.emplid AND
        plan.acad_career = prog.acad_career AND
        plan.stdnt_car_nbr = prog.stdnt_car_nbr AND
        plan.effdt = prog.effdt AND
        plan.effseq = prog.effseq 
    WHERE 
        plan.acad_plan IN $plans
        AND prog.prog_status = 'AC' 
        AND car_term.withdraw_code = 'NWD'
        AND car_term.strm < $registration_semester
        AND car_term.strm >= $third_prior_semester
        AND plan.effdt = (
            SELECT MAX(temp_plan.effdt) 
            FROM ps_acad_plan temp_plan
            WHERE plan.emplid = temp_plan.emplid AND
                  plan.acad_career = temp_plan.acad_career AND 
                  plan.acad_plan = temp_plan.acad_plan AND
                  temp_plan.effdt < $effective_date)
        AND plan.effseq = (
            SELECT MAX(temp_plan_2.effseq)
            FROM ps_acad_plan temp_plan_2
            WHERE plan.emplid = temp_plan_2.emplid AND
                  plan.acad_career = temp_plan_2.acad_career AND 
                  plan.acad_plan = temp_plan_2.acad_plan AND 
                  plan.effdt = temp_plan_2.effdt)
        """)
    default_arguments = {
        'plans': ['CMPTMAJ'],
        'effective_date': datetime.datetime.now(), 
        'registration_semester': registration_semester(),
        'third_prior_semester': registration_semester().increment(-3)
        }

    def result(self):
        return super(ActivePlanQueryWithReqTerm, self).result().flatten("EMPLID")

class ActivePlanQuery(ActivePlanQueryWithReqTerm):
    title = "Active Plan Query"
    description = "Fetch a list of active students by academic plan"
    # This is likely to produce duplicates - students that are enrolled in more than one academic plan.

    def result(self):
        tempresult = super(ActivePlanQuery, self).result().flatten("EMPLID")
        tempresult.remove_column("REQ_TERM")
        return tempresult

class SubplanQuery(DB2_Query):

    title = "Subplan Query"
    description = "Fetch a list of student-to-subplan mappings within a set of plans" 
    # This is likely to produce duplicates - students that are enrolled in more than one subplan. 

    query = string.Template("""
    SELECT DISTINCT 
        plan.emplid,
        plan.acad_sub_plan
    FROM 
        ps_acad_subplan plan
    INNER JOIN
        ps_stdnt_car_term car_term 
        ON
        plan.emplid = car_term.emplid AND
        plan.acad_career = car_term.acad_career AND
        plan.stdnt_car_nbr = car_term.stdnt_car_nbr
    INNER JOIN 
        ps_acad_prog prog
        ON
        plan.emplid = prog.emplid AND
        plan.acad_career = prog.acad_career AND
        plan.stdnt_car_nbr = prog.stdnt_car_nbr
    WHERE 
        prog.prog_status = 'AC' 
        AND car_term.withdraw_code = 'NWD'
        AND car_term.strm < $registration_semester
        AND car_term.strm >= $third_prior_semester
        AND plan.effdt = (
            SELECT MAX(temp_plan.effdt) 
            FROM ps_acad_subplan temp_plan
            WHERE plan.emplid = temp_plan.emplid AND
                  plan.acad_career = temp_plan.acad_career AND 
                  plan.acad_plan = temp_plan.acad_plan AND
                  plan.acad_sub_plan = temp_plan.acad_sub_plan AND
                  temp_plan.effdt < $effective_date)
        AND plan.effseq = (
            SELECT MAX(temp_plan_2.effseq)
            FROM ps_acad_subplan temp_plan_2
            WHERE plan.emplid = temp_plan_2.emplid AND
                  plan.acad_career = temp_plan_2.acad_career AND 
                  plan.acad_plan = temp_plan_2.acad_plan AND 
                  plan.acad_sub_plan = temp_plan_2.acad_sub_plan AND
                  plan.effdt = temp_plan_2.effdt AND
                  temp_plan_2.effdt < $effective_date)
        """)
    default_arguments = {
        'effective_date': datetime.datetime.now(), 
        'registration_semester': registration_semester(),
        'third_prior_semester': registration_semester().increment(-3)
        }
        

class ActiveInProgramOrPlanQuery(object):
    
    title = "Program And Plan Query"
    description = """Fetch a table of students, emplid-only, 
        who are active (have taken a course in the past 3 semesters), 
        and taking a program or plan in the provided list. """
    query = string.Template("""None""")

    def __init__( self, arguments ):
        self.arguments = arguments
    
    def produce_emplid_table(self, programs, plans):
        emplids = (plans.column_as_list("EMPLID") + programs.column_as_list("EMPLID"))
        unique_emplids = list({}.fromkeys(emplids).keys())
        
        just_emplid_table = Table()
        just_emplid_table.append_column("EMPLID")
        for emplid in unique_emplids:
            just_emplid_table.append_row( [ emplid ] )

        just_emplid_table.left_join( programs, "EMPLID" )
        just_emplid_table.left_join( plans, "EMPLID" )
        just_emplid_table.compute_column( "CAREER", lambda x: x["ACAD_CAREER"] or x["ACAD_CAREER_JOIN"] )
        just_emplid_table.compute_column( "PROGRAM", lambda x: x["ACAD_PROG"] or x["ACAD_PROG_JOIN"] )
        just_emplid_table.remove_column( "ACAD_CAREER" )
        just_emplid_table.remove_column( "ACAD_CAREER_JOIN" )
        just_emplid_table.remove_column( "ACAD_PROG" )
        just_emplid_table.remove_column( "ACAD_PROG_JOIN" )
        just_emplid_table.flatten('EMPLID')
        
        return just_emplid_table
    
    def result(self):
        program_query = ActiveProgramQuery( {'programs':self.arguments['programs'] } ) 
        plan_query = ActivePlanQuery( {'plans': self.arguments['plans']} )

        programs = program_query.result()
        plans = plan_query.result()
        return self.produce_emplid_table( programs, plans )

