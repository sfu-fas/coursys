from ..report import Report
from ..queries import CGPAQuery, ActiveInProgramOrPlanQuery, EmailQuery, NameQuery, PreferredPhoneQuery
from .. import rules

import copy

class BadFirstSemesterReport( Report ):
    title = "Bad First Semester Report"
    description = "This report lists FAS undergrad students with a GPA below 2.0, with less than 15 credits of courses." 

    def run( self ):
        # Queries 
        student_query = ActiveInProgramOrPlanQuery( {'programs':rules.program_groups['fas_undergrad_programs'], 
                                                     'plans':rules.plan_groups['fas_plans']} )
        students = student_query.result()

        gpa_query = CGPAQuery() 
        gpas = gpa_query.result()

        email_query = EmailQuery()
        email = email_query.result()
        email.filter( EmailQuery.campus_email )

        name_query = NameQuery()
        names = name_query.result()
        
        #Filters 
        def plan_or_program(row_map, plans, programs):
            row_programs = [x.strip() for x in row_map['PROGRAM'].split(",")]
            return row_map['ACAD_PLAN'] in plans or any( [row_program in programs for row_program in row_programs] )

        def gpa_below_2_but_not_zero( row_map ):
            try:
                return float(row_map["CUM_GPA"]) < 2 and float(row_map["CUM_GPA"]) > 0
            except:
                print(row_map)
        
        def credits_below_15_but_not_zero( row_map ):
            try:
                return float(row_map["CREDITS"]) < 18 and float(row_map["CREDITS"]) > 0
            except:
                print(row_map)

        def student_in_undergrad_cmpt( row_map ):
            return plan_or_program( row_map, rules.plan_groups['cmpt_plans'], rules.program_groups['cmpt_undergrad_programs'] )
        
        def student_in_undergrad_engi( row_map ):
            return plan_or_program( row_map, rules.plan_groups['ensc_plans'], rules.program_groups['ensc_undergrad_programs'] )

        def student_in_undergrad_bgs( row_map ):
            return plan_or_program( row_map, rules.plan_groups['bgs_plans'], rules.program_groups['bgs_undergrad_programs'] )

        students.left_join( gpas, "EMPLID" )
        students.filter( gpa_below_2_but_not_zero )
        students.filter( credits_below_15_but_not_zero )
        students.left_join( names, "EMPLID" )
        students.left_join( email, "EMPLID" )
        
        students = students.subset( ["EMPLID", "PROGRAM", "ACAD_PLAN", "CUM_GPA", "CREDITS", "NAME_DISPLAY", "EMAIL_ADDR"] ) 

        cmpt_table = copy.deepcopy( students )
        cmpt_table.filter( student_in_undergrad_cmpt )
        engi_table = copy.deepcopy( students )
        engi_table.filter( student_in_undergrad_engi )
        bgs_table = copy.deepcopy( students )
        bgs_table.filter( student_in_undergrad_bgs )
        
        cmpt_table.title = "CMPT Students"
        cmpt_table.description = "Students with GPA < 2 and Credits < 15 in a CMPT program or plan."
        engi_table.title = "ENGI Students"
        engi_table.description = "Students with GPA < 2 and Credits < 15 in an Engineering program or plan."
        bgs_table.title = "BGS Students"
        bgs_table.description = "Students with GPA < 2 and Credits < 15 in a BGS program or plan."

        # Output
        self.artifacts.append(cmpt_table)
        self.artifacts.append(engi_table)
        self.artifacts.append(bgs_table)
