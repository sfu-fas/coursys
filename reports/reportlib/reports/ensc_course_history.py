from reports.reportlib.report import Report
from reports.reportlib.table import Table
from coredata.models import Semester, Unit, CourseOffering, CAMPUSES_SHORT, WEEKDAYS
from faculty.models import CareerEvent


class ENSCCourseHistoryReport(Report):
    title = "ENSC Course History"
    description = "This report summarizes course information for ENSC, including enrollment, instructors, etc"

    def run(self):
        sems = Semester.objects.filter(name__gte='1001', name__lte=Semester.next_starting().name)
        u = Unit.objects.get(label='ENSC')
        courses = CourseOffering.objects.prefetch_related('meeting_time').filter(semester__in=sems, owner=u,
                                                                                 graded=True).exclude(
            flags=CourseOffering.flags.combined).exclude(subject='DDP').order_by('semester', 'subject', 'number')
        course_history = Table()
        course_history.append_column('Semester')
        course_history.append_column('Course')
        course_history.append_column('Instructor')
        course_history.append_column('Enrolment')
        course_history.append_column('Campus')
        course_history.append_column('Joint With')
        course_history.append_column('Lecture Times')
        course_history.append_column('Instructor(s) Rank(s)')
        for course in courses:
            semester = course.semester.label()
            label = course.name()
            instr = course.instructors_printing_str()
            enrl = '%i/%i' % (course.enrl_tot, course.enrl_cap)
            if course.campus in CAMPUSES_SHORT:
                campus = CAMPUSES_SHORT[course.campus]
            else:
                campus = 'Unknown'
            if course.config.get('joint_with'):
                joint = str(', '.join(course.config.get('joint_with')))
            else:
                joint = ''
            meeting_times = ''
            mt = [t for t in course.meeting_time.all() if t.meeting_type == 'LEC']
            if mt:
                meeting_times = ', '.join(str("%s %s-%s" % (WEEKDAYS[t.weekday], t.start_time, t.end_time)) for t in mt)
            ranks = "; ".join(CareerEvent.ranks_as_of_semester(p.id, course.semester) for p in course.instructors())
            course_history.append_row([semester, label, instr, enrl, campus, joint, meeting_times, ranks])
        self.artifacts.append(course_history)




