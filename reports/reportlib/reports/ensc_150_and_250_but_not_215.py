from ..report import Report
from ..queries import ActivePlanQuery, SingleCourseQuery, SubplanQuery, CGPAQuery, EmailQuery
from .. import rules

import copy

class Ensc150And250ButNot215StudentReport( Report ):
    """
    Contact: Tara Smith

    I was asked this morning for the number of students who have taken ENSC 150 and (ENSC 250 or CMPT 250) but
    not ENSC 215.

    """

    def run( self ):
        # Queries 
        student_query = ActivePlanQuery( {'plans':['ENSCPRO']} )
        students = student_query.result()

        subplan_query = SubplanQuery( )
        subplans = subplan_query.result()
        subplans.flatten("EMPLID")

        students.left_join(subplans, "EMPLID")
        
        students.title = "Master Table" 

        def emplids_in_course(subject, catalog_nbr):
            course_query = SingleCourseQuery( {'subject': subject, 'catalog_nbr': catalog_nbr} )
            course = course_query.result()
            emplids = set(course.column_as_list('EMPLID'))
            del course_query
            del course
            return emplids

        ensc_150_emplids = emplids_in_course('ENSC', '150')
        cmpt_150_emplids = emplids_in_course('CMPT', '150')
        ensc_250_emplids = emplids_in_course('ENSC', '250')
        cmpt_250_emplids = emplids_in_course('CMPT', '250')
        ensc_215_emplids = emplids_in_course('ENSC', '215')

        students.compute_column('HAS_ENSC_150', lambda x: x['EMPLID'] in ensc_150_emplids)
        students.compute_column('HAS_CMPT_150', lambda x: x['EMPLID'] in cmpt_150_emplids)
        students.compute_column('HAS_ENSC_250', lambda x: x['EMPLID'] in ensc_250_emplids)
        students.compute_column('HAS_CMPT_250', lambda x: x['EMPLID'] in cmpt_250_emplids)
        students.compute_column('HAS_ENSC_215', lambda x: x['EMPLID'] in ensc_215_emplids)

        email_query = EmailQuery()
        email = email_query.result()
        email.filter(EmailQuery.campus_email)
        email.remove_column("PREF_EMAIL_FLAG")
        email.remove_column("E_ADDR_TYPE")

        students.left_join(email, "EMPLID")
        
        target_students = copy.deepcopy(students)
        target_students.title = "Students with ENSC 150 and (ENSC or CMPT 250) but not ENSC 215"

        target_students.filter( lambda x: (x['HAS_ENSC_150'] and 
                                    (x['HAS_ENSC_250'] or x['HAS_CMPT_250']) 
                                    and not x['HAS_ENSC_215']) )
        target_students.remove_column("HAS_CMPT_150")

        target_students_2 = copy.deepcopy(students)
        target_students_2.title = "Students with (ENSC 150 or CMPT 150) and no (ENSC 215 or ENSC 250)"
        target_students_2.filter( lambda x: ((x['HAS_ENSC_150'] or x['HAS_CMPT_150']) and 
                                    not (x['HAS_ENSC_215'] or x['HAS_ENSC_250'])) )
        target_students_2.remove_column("HAS_CMPT_250")

        students.flatten("EMPLID")
        target_students.flatten("EMPLID")
        target_students_2.flatten("EMPLID")

        self.artifacts.append(students)
        self.artifacts.append(target_students)
        self.artifacts.append(target_students_2)

