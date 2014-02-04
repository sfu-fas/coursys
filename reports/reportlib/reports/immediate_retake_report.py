from reports.reportlib.report import Report
from reports.reportlib.queries import StudentCourseQuery, RepeatableCourseQuery
from reports.reportlib.semester import registration_semester, current_semester

class ImmediateRetakeReport( Report ):
    title = "Immediate Retake Report"
    description = "This report tracks students who are registered for the same course, this semester, as last semester." 

    def run( self ):
        #Queries 
        repeatable_course_query = RepeatableCourseQuery() 
        repeatable_courses = repeatable_course_query.result() 
        repeatable_courses.generate_index("CRSE_ID")

        current_semester_query = StudentCourseQuery( {'semester':registration_semester()} )
        current_semester_table = current_semester_query.result()


        def create_course_join_column( row_map ):
            if row_map['EQUIV_CRSE_ID'] != "":
                return "-".join( [row_map[column] for column in ["EMPLID", "EQUIV_CRSE_ID"]] )
            else:
                return "-".join( [row_map[column] for column in ["EMPLID", "SUBJECT", "CATALOG_NBR"]] )
        
        current_semester_table.compute_column( "STUDENT_COURSE", create_course_join_column ) 
        current_semester_table.generate_index( "STUDENT_COURSE" )

        previous_semester_query = StudentCourseQuery( {'semester':registration_semester().increment(-1)} )
        previous_semester_table = previous_semester_query.result()
        previous_semester_table.compute_column( "STUDENT_COURSE", create_course_join_column )
        previous_semester_table.generate_index( "STUDENT_COURSE" )

        #Filters 
        def subject_in_fas( row_map ):
            """ Discards courses that aren't in CMPT, MACM, or ENSC """
            return row_map["SUBJECT"] in ["CMPT", "MACM", "ENSC"]
        
        def ignore_repeatable_courses( row_map ):
            """ Discards courses that are flagged as 'repeatable' """
            return not repeatable_courses.contains( "CRSE_ID", row_map["CRSE_ID"] )
        
        def subject_in_fas_and_not_repeatable( row_map):
            return subject_in_fas(row_map) and ignore_repeatable_courses(row_map)

        def has_no_grade( row_map):
            """ Discards courses that have a grade """
            return row_map["CRSE_GRADE_INPUT"] == ''
        
        current_semester_table.filter( subject_in_fas_and_not_repeatable )
        previous_semester_table.filter( subject_in_fas_and_not_repeatable )
        previous_semester_table.filter( has_no_grade )

        # Transforms 
        current_semester_table.inner_join( previous_semester_table, "STUDENT_COURSE" )

        current_semester_table.compute_column("COURSE", lambda x: x["SUBJECT"] + " " + x["CATALOG_NBR"] )
        current_semester_table.compute_column("SECOND_COURSE", lambda x: x["SUBJECT_JOIN"] + " " + x["CATALOG_NBR_JOIN"] ) 
        current_semester_table.compute_column("DESCRIPTION", lambda x: "This student is registered for " + x['COURSE'] + " next semester, even though he is currently enrolled in " + x['SECOND_COURSE'] + " this semester." )

        output_table = current_semester_table.subset( ["EMPLID", "COURSE", "DESCRIPTION"] ) 
        output_table.title=self.title
        output_table.description=self.description

        # Output
        self.artifacts.append( output_table )
        self.artifacts.append( current_semester_query ) 
        self.artifacts.append( previous_semester_query )
        self.artifacts.append( repeatable_course_query )
