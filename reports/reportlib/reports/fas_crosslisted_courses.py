from ..report import Report
from ..table import Table
from coredata.models import Semester, Unit, CourseOffering, CAMPUSES_SHORT

class FASCrosslistedCoursesReport(Report):
    title = "FAS Crosslisted Courses"
    description = "A report of all courses that are crosslisted from the previous 5 years"

    def run(self):
        # previous 5 years
        start_semester = Semester.current().offset(-15)
        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE', 'APSC'])
        course_offerings = CourseOffering.objects.filter(owner__in=units, semester__gte=start_semester)
        # no locally-merged courses
        course_offerings = course_offerings.exclude(flags=CourseOffering.flags.combined)
        # no cancelled courses
        course_offerings = course_offerings.exclude(component='CAN')

        results = Table()
        results.append_column('Semester')
        results.append_column('Course Unit')
        results.append_column('Course')
        results.append_column('Title')
        results.append_column('Enrolment')

        results.append_column('Crosslisted Course Unit')
        results.append_column('Crosslisted Course')
        results.append_column('Crosslisted Title')
        results.append_column('Crosslisted Enrolment')

        results.append_column('Instructor(s)')
        results.append_column('Campus')

        # array of course offering combos that are joint, making sure to account for multiples
        unique_joint_offerings = set()
        for co in course_offerings:
            joint_with = co.config.get('joint_with')
            if joint_with:
                if len(joint_with) > 1:
                    for slug in joint_with:
                        unique_joint_offerings.add(tuple(sorted([co.slug, slug])))
                else:
                    unique_joint_offerings.add(tuple(sorted([co.slug, joint_with[0]])))
        unique_joint_offerings = [list(offering_combo) for offering_combo in unique_joint_offerings]

        for o in unique_joint_offerings:
            if len(o) == 2:
                try:
                    co_1 = CourseOffering.objects.get(slug=o[0])
                    co_2 = CourseOffering.objects.get(slug=o[1])
                except CourseOffering.DoesNotExist:
                    continue
                
                # semester should always be the same
                semester = co_1.semester.label()

                # instructors should always be the same
                instructors = co_1.instructors_printing_str()

                # campus should always be the same
                campus = CAMPUSES_SHORT[co_1.campus]

                # units
                co_1_unit = co_1.owner.label
                co_2_unit = co_2.owner.label
                
                # course names
                co_1_course_name = '%s %s %s' % (co_1.subject, co_1.number, co_1.section)
                co_2_course_name = '%s %s %s' % (co_2.subject, co_2.number, co_2.section)
                
                #course titles
                co_1_title = co_1.title
                co_2_title = co_2.title
                    
                # enrolment
                co_1_course_enrol = 'Tot: %i / Cap: %i' % (co_1.enrl_tot, co_1.enrl_cap)
                co_2_course_enrol = 'Tot: %i / Cap: %i' % (co_2.enrl_tot, co_2.enrl_cap)

                if co_1.wait_tot:
                    co_1_course_enrol += ' (+ Wait: %i)' % (co_1.wait_tot)
                if co_2.wait_tot:
                    co_2_course_enrol += ' (+ Wait: %i)' % (co_2.wait_tot)
                                    
                results.append_row([semester, co_1_unit, co_1_course_name, co_1_title, co_1_course_enrol, co_2_unit, co_2_course_name, co_2_title, co_2_course_enrol, instructors, campus])

        self.artifacts.append(results)
