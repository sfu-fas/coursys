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
        PROG.EMPLID,
        PROG.ACAD_CAREER,
        PROG.ACAD_PROG
    FROM 
        PS_ACAD_PROG PROG
    INNER JOIN
        PS_STDNT_CAR_TERM CAR_TERM 
        ON
        PROG.EMPLID = CAR_TERM.EMPLID AND
        PROG.ACAD_CAREER = CAR_TERM.ACAD_CAREER AND
        PROG.STDNT_CAR_NBR = CAR_TERM.STDNT_CAR_NBR
    WHERE 
        PROG.ACAD_PROG IN $PROGRAMS
        AND PROG.PROG_STATUS = 'AC' 
        AND CAR_TERM.WITHDRAW_CODE = 'NWD'
        AND CAR_TERM.STRM < $registration_semester
        AND CAR_TERM.STRM >= $third_prior_semester
        AND PROG.EFFDT = (
            SELECT MAX(TEMP_PROG.EFFDT) 
            FROM PS_ACAD_PROG TEMP_PROG
            WHERE PROG.EMPLID = TEMP_PROG.EMPLID AND
                  PROG.ACAD_CAREER = TEMP_PROG.ACAD_CAREER AND 
                  PROG.ACAD_PROG = TEMP_PROG.ACAD_PROG AND
                  TEMP_PROG.EFFDT < $effective_date)
        AND PROG.EFFSEQ = (
            SELECT MAX(TEMP_PROG_2.EFFSEQ)
            FROM PS_ACAD_PROG TEMP_PROG_2
            WHERE PROG.EMPLID = TEMP_PROG_2.EMPLID AND
                  PROG.ACAD_CAREER = TEMP_PROG_2.ACAD_CAREER AND 
                  PROG.ACAD_PROG = TEMP_PROG_2.ACAD_PROG AND
                  PROG.EFFDT = TEMP_PROG_2.EFFDT)
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
        PLAN.EMPLID,
        PLAN.ACAD_CAREER,
        PROG.ACAD_PROG,
        PLAN.ACAD_PLAN,
        PLAN.REQ_TERM
    FROM 
        PS_ACAD_PLAN PLAN
    INNER JOIN
        PS_STDNT_CAR_TERM CAR_TERM 
        ON
        PLAN.EMPLID = CAR_TERM.EMPLID AND
        PLAN.ACAD_CAREER = CAR_TERM.ACAD_CAREER AND
        PLAN.STDNT_CAR_NBR = CAR_TERM.STDNT_CAR_NBR
    INNER JOIN 
        PS_ACAD_PROG PROG
        ON
        PLAN.EMPLID = PROG.EMPLID AND
        PLAN.ACAD_CAREER = PROG.ACAD_CAREER AND
        PLAN.STDNT_CAR_NBR = PROG.STDNT_CAR_NBR AND
        PLAN.EFFDT = PROG.EFFDT AND
        PLAN.EFFSEQ = PROG.EFFSEQ 
    WHERE 
        PLAN.ACAD_PLAN IN $plans
        AND PROG.PROG_STATUS = 'AC' 
        AND CAR_TERM.WITHDRAW_CODE = 'NWD'
        AND CAR_TERM.STRM < $registration_semester
        AND CAR_TERM.STRM >= $third_prior_semester
        AND PLAN.EFFDT = (
            SELECT MAX(TEMP_PLAN.EFFDT) 
            FROM PS_ACAD_PLAN TEMP_PLAN
            WHERE PLAN.EMPLID = TEMP_PLAN.EMPLID AND
                  PLAN.ACAD_CAREER = TEMP_PLAN.ACAD_CAREER AND 
                  PLAN.ACAD_PLAN = TEMP_PLAN.ACAD_PLAN AND
                  TEMP_PLAN.EFFDT < $effective_date)
        AND PLAN.EFFSEQ = (
            SELECT MAX(TEMP_PLAN_2.EFFSEQ)
            FROM PS_ACAD_PLAN TEMP_PLAN_2
            WHERE PLAN.EMPLID = TEMP_PLAN_2.EMPLID AND
                  PLAN.ACAD_CAREER = TEMP_PLAN_2.ACAD_CAREER AND 
                  PLAN.ACAD_PLAN = TEMP_PLAN_2.ACAD_PLAN AND 
                  PLAN.EFFDT = TEMP_PLAN_2.EFFDT)
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
        PLAN.EMPLID,
        PLAN.ACAD_SUB_PLAN
    FROM 
        PS_ACAD_SUBPLAN PLAN
    INNER JOIN
        PS_STDNT_CAR_TERM CAR_TERM 
        ON
        PLAN.EMPLID = CAR_TERM.EMPLID AND
        PLAN.ACAD_CAREER = CAR_TERM.ACAD_CAREER AND
        PLAN.STDNT_CAR_NBR = CAR_TERM.STDNT_CAR_NBR
    INNER JOIN 
        PS_ACAD_PROG PROG
        ON
        PLAN.EMPLID = PROG.EMPLID AND
        PLAN.ACAD_CAREER = PROG.ACAD_CAREER AND
        PLAN.STDNT_CAR_NBR = PROG.STDNT_CAR_NBR
    WHERE 
        PROG.PROG_STATUS = 'AC' 
        AND CAR_TERM.WITHDRAW_CODE = 'NWD'
        AND CAR_TERM.STRM < $registration_semester
        AND CAR_TERM.STRM >= $third_prior_semester
        AND PLAN.EFFDT = (
            SELECT MAX(TEMP_PLAN.EFFDT) 
            FROM PS_ACAD_SUBPLAN TEMP_PLAN
            WHERE PLAN.EMPLID = TEMP_PLAN.EMPLID AND
                  PLAN.ACAD_CAREER = TEMP_PLAN.ACAD_CAREER AND 
                  PLAN.ACAD_PLAN = TEMP_PLAN.ACAD_PLAN AND
                  PLAN.ACAD_SUB_PLAN = TEMP_PLAN.ACAD_SUB_PLAN AND
                  TEMP_PLAN.EFFDT < $effective_date)
        AND PLAN.EFFSEQ = (
            SELECT MAX(TEMP_PLAN_2.EFFSEQ)
            FROM PS_ACAD_SUBPLAN TEMP_PLAN_2
            WHERE PLAN.EMPLID = TEMP_PLAN_2.EMPLID AND
                  PLAN.ACAD_CAREER = TEMP_PLAN_2.ACAD_CAREER AND 
                  PLAN.ACAD_PLAN = TEMP_PLAN_2.ACAD_PLAN AND 
                  PLAN.ACAD_SUB_PLAN = TEMP_PLAN_2.ACAD_SUB_PLAN AND
                  PLAN.EFFDT = TEMP_PLAN_2.EFFDT AND
                  TEMP_PLAN_2.EFFDT < $effective_date)
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

