from ..report import Report
from ..table import Table
from coredata.models import CAMPUSES_SHORT, Semester, CourseOffering, Unit
from django.urls import reverse
from django.conf import settings

class FASBrowseCourseOfferingsReport(Report):
    title = "FAS Course Offerings"
    description = "A report of all FAS course offerings from the past 10 years"

    def run(self):
        results = Table()
        results.append_column('Semester')
        results.append_column('Course')
        results.append_column('Title')
        results.append_column('Enroll')
        results.append_column('Instructor(s)')
        results.append_column('Campus')
        results.append_column('Course URL') 

        start_semester = Semester.current().offset(-30) # 10 years ago
        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE'])
        course_offerings = CourseOffering.objects.filter(owner__in=units, semester__gte=start_semester)
        # no locally-merged courses
        course_offerings = course_offerings.exclude(flags=CourseOffering.flags.combined)
        # no cancelled courses
        course_offerings = course_offerings.exclude(component='CAN')

        for c in course_offerings:
            semester = c.semester.label()
            course = '%s\u00a0%s\u00a0%s' % (c.subject, c.number, c.section)
            title = c.title
            enroll = '%i/%i' % (c.enrl_tot, c.enrl_cap)
            instructors = c.instructors_printing_str()
            campus = CAMPUSES_SHORT[c.campus]
            course_url = settings.BASE_ABS_URL + reverse('browse:browse_courses_info', kwargs={'course_slug': c.slug})

            results.append_row([semester, course, title, enroll, instructors, campus, course_url])
            
        self.artifacts.append(results)

