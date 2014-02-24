from ..report import Report
from ..queries import CGPAQuery, ActiveInProgramOrPlanQuery, EmailQuery, NameQuery, PreferredPhoneQuery, OriginQuery 
from .. import rules

import copy

class FasStudentReport( Report ):

    def run( self ):
        # Queries 
        student_query = ActiveInProgramOrPlanQuery( {'programs':rules.program_groups['fas_undergrad_programs'], \
                                                     'plans':rules.plan_groups['fas_plans']} )
        students = student_query.result()

        gpa_query = CGPAQuery() 
        gpas = gpa_query.result()

        email_query = EmailQuery()
        email = email_query.result()
        email.filter( EmailQuery.preferred_email )

        phone_query = PreferredPhoneQuery()
        phone = phone_query.result()

        name_query = NameQuery()
        names = name_query.result()

        students.inner_join( gpas, "EMPLID" )
        students.left_join( names, "EMPLID" )
        students.left_join( email, "EMPLID" )
        students.left_join( phone, "EMPLID" )
        students.compute_column( "PREFERRED_PHONE", PreferredPhoneQuery.combined_number ) 
        
        students = students.subset( ["EMPLID", "CAREER", "PROGRAM", "ACAD_PLAN", "CUM_GPA", 
                                        "CREDITS", "EMAIL_ADDR", "NAME_DISPLAY", "PREFERRED_PHONE"] ) 
        students.headers = ["EMPLID", "CAREER", "PROGRAM", "PLAN", "CGPA", 
                                "CREDITS",  "PREF. EMAIL", "NAME", "PREF. PHONE"] 

        #Filters 
        #def gpa_above_2_5( row_map ):
        #    return float(row_map["CGPA"]) > 2.5

        #def gpa_below_2_4( row_map ):
        #    return float(row_map["CGPA"]) < 2.4 and float(row_map["CGPA"]) > 0

        #high_gpa = copy.deepcopy( students )
        #low_gpa = copy.deepcopy( students )

        #high_gpa.filter( gpa_above_2_5 )
        #low_gpa.filter( gpa_below_2_4 )
        
        #students.title=self.title
        #students.description="All active FAS students."

        # Output
        self.artifacts.append(students)
        #self.artifacts.append(high_gpa)
        #self.artifacts.append(low_gpa)

