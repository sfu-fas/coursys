from ..report import Report
from ..queries import ActivePlanQuery, SingleCourseQuery, CGPAQuery, EmailQuery
from .. import rules

import copy

class FasStudentReport( Report ):
    """
    Contact: Tara Smith

    1) ENSCPRO students who have completed 70 units or more who have not taken 
        one of ENSC 194, ENSC 195 or ENSC 196
    2) ENSCPRO students who have completed 80 units or more who have not taken 
        one of ENSC 194, ENSC 195 or ENSC 196
    3) ENSCPRO students who have completed 90 units or more who have not taken 
        one of ENSC 194, ENSC 195 or ENSC 196
    4) ENSCPRO students who have completed 100 units or more who have not taken 
        one of ENSC 194, ENSC 195 or ENSC 196
    5) ENSCPRO students who have completed 90 units or more who have not taken 
        one of ENSC 295 or ENSC 296
    6) ENSCPRO students who have completed 100 units or more who have not taken 
        one of ENSC 295 or ENSC 296

    It could be only one query if we were able to sort the data by the number 
    of units completed and identify which of ENSC 194, ENSC 195, ENSC 196, 
    ENSC 295, or ENSC 296 each student has completed. 
    
    Ideally, the CGPA, academic subplan, email address and SFU ID would be 
    helpful if they could be included.
    """

    def run( self ):
        # Queries 
        student_query = ActivePlanQuery( {'plans':['ENSCPRO']} )
        students = student_query.result()
        
        students.title = "Master Table" 

        def emplids_in_course(subject, catalog_nbr):
            course_query = SingleCourseQuery( {'subject': subject, 'catalog_nbr': catalog_nbr} )
            course = course_query.result()
            emplids = set(course.column_as_list('EMPLID'))
            del course_query
            del course
            return emplids

        ensc_194_emplids = emplids_in_course('ENSC', '194')
        ensc_195_emplids = emplids_in_course('ENSC', '195')
        ensc_196_emplids = emplids_in_course('ENSC', '196')
        ensc_295_emplids = emplids_in_course('ENSC', '295')
        ensc_296_emplids = emplids_in_course('ENSC', '296')

        students.compute_column('HAS_ENSC_194', lambda x: x['EMPLID'] in ensc_194_emplids)
        students.compute_column('HAS_ENSC_195', lambda x: x['EMPLID'] in ensc_195_emplids)
        students.compute_column('HAS_ENSC_196', lambda x: x['EMPLID'] in ensc_196_emplids)
        students.compute_column('HAS_ENSC_295', lambda x: x['EMPLID'] in ensc_295_emplids)
        students.compute_column('HAS_ENSC_296', lambda x: x['EMPLID'] in ensc_296_emplids)

        gpa_and_credit_query = CGPAQuery() 
        gpas = gpa_and_credit_query.result()
        
        email_query = EmailQuery()
        email = email_query.result()
        email.filter(EmailQuery.campus_email)
        email.remove_column("PREF_EMAIL_FLAG")

        students.left_join(gpas, "EMPLID")
        students.left_join(email, "EMPLID")

        students_70 = copy.deepcopy( students )
        students_70.title = "Students with >70 Credits and no ENSC 194-196"

        def floaty(x):
            try:
                return float(x)
            except:
                return 0.0

        students_70.filter( lambda x: floaty(x['CREDITS']) > 69.9 )
        students_70.filter( lambda x: not x['HAS_ENSC_194'] or not x['HAS_ENSC_195'] or not x['HAS_ENSC_196'] )

        students_100 = copy.deepcopy(students)
        students_100.title = "Students with >100 Credits and no ENSC 295-296"
        students_100.filter( lambda x: floaty(x['CREDITS']) > 99.9 )
        students_100.filter( lambda x: not x['HAS_ENSC_295'] or not x['HAS_ENSC_296'] )

        self.artifacts.append(students)
        self.artifacts.append(students_70)
        self.artifacts.append(students_100)

