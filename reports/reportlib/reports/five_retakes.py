from ..report import Report
from ..queries import StudentCourseQuery, RepeatableCourseQuery, ActiveInProgramOrPlanQuery, EmailQuery, NameQuery
from ..semester import registration_semester, current_semester, semester_range 
from .. import rules
from ..table import Table 

class FiveRetakeReport( Report ):
    title = "Five Retake Report"
    description = "This report tracks students who have retaken more than five courses." 

    def run( self ):
        # Last 6 years = Last 18 semesters
        semesters = semester_range( current_semester().increment(-18), current_semester() )

        # Students of interest
        student_query = ActiveInProgramOrPlanQuery( {'programs':rules.program_groups['fas_undergrad_programs'], \
                                                     'plans':rules.plan_groups['fas_plans']} )
        students = student_query.result()
        students_of_interest = students.column_as_list("EMPLID")
        
        def student_of_interest(row_map):
            return row_map['EMPLID'] in students_of_interest
        
        def subject_in_fas(row_map):
            """ Discards courses that aren't in CMPT, MACM, or ENSC """
            return row_map["SUBJECT"] in ["CMPT", "MACM", "MSE", "ENSC"]

        def xx_in_number(row_map):
            """ Discards courses that have a number like XX1 or 1XX """
            return "XX" not in row_map["CATALOG_NBR"]
        
        def ignore_repeatable_courses(row_map):
            """ Discards courses that are flagged as 'repeatable' """
            return not repeatable_courses.contains( "CRSE_ID", row_map["CRSE_ID"] )
        
        def compound_filter(row_map):
            return (student_of_interest(row_map) and 
                    ignore_repeatable_courses(row_map) and
                    xx_in_number(row_map))
        
        def create_course_join_column(row_map):
            if row_map['EQUIV_CRSE_ID'] != "":
                return row_map["EQUIV_CRSE_ID"]
            else:
                return "-".join( [row_map[column] for column in ["SUBJECT", "CATALOG_NBR"]] )

        student_courses = {}
        student_retakes = {}

        repeatable_course_query = RepeatableCourseQuery() 
        repeatable_courses = repeatable_course_query.result() 
        repeatable_courses.generate_index("CRSE_ID")

        for semester in semesters:
            current_semester_query = StudentCourseQuery( {'semester':semester} )
            current_semester_table = current_semester_query.result()
            current_semester_table.filter( compound_filter )
            current_semester_table.compute_column( "STUDENT_COURSE", create_course_join_column )
            for row in current_semester_table.row_maps():
                emplid = row["EMPLID"]
                course = row["STUDENT_COURSE"]
                if not emplid in student_courses:
                    student_courses[emplid] = [] 
                if course in student_courses[emplid]:
                    if not emplid in student_retakes:
                        student_retakes[emplid] = []
                    course_descriptor = row["SUBJECT"] + "-" + row["CATALOG_NBR"] + " (" + str(semester) + ")"
                    student_retakes[emplid].append(course_descriptor)
                else: 
                    student_courses[emplid].append(course)
        
        
        self.logger.log( "----------------------------------------" )
        self.logger.log( "----------------------------------------" )
        self.logger.log( "----------------------------------------" )

        output_table = Table()
        output_table.title = "Retake Report"
        output_table.append_column("EMPLID")
        output_table.append_column("N_RETAKES")
        output_table.append_column("RETAKES")
        
        for key, value in student_retakes.items():
            if len(value) > 1:
                output_table.append_row( [ key, len(value), value ] )
        
        email_query = EmailQuery()
        email = email_query.result()
        email.filter( EmailQuery.preferred_email )

        name_query = NameQuery()
        names = name_query.result()
        
        output_table.left_join( names, "EMPLID" )
        output_table.left_join( email, "EMPLID" )
        output_table.compute_column("RETAKE", lambda x: ", ".join(x['RETAKES']))
        output_table = output_table.subset( ['EMPLID', 'N_RETAKES', 'RETAKE', 'NAME_DISPLAY', 'EMAIL_ADDR'] )

        self.artifacts.append(output_table)
