from reports.reportlib.report import Report
from reports.reportlib.table import Table
from coredata.models import Semester, Unit, CourseOffering, CAMPUSES_SHORT, WEEKDAYS


class CMPTCourseHistoryReport(Report):
    title = "CMPT Course History"
    description = "This report summarizes course information for CMPT, including enrollment, instructors, etc"

    def run(self):
        sems = Semester.objects.filter(name__gte='1001', name__lte=Semester.next_starting().name)
        u = Unit.objects.get(label='CMPT')
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
        for course in courses:
            semester = course.semester.label()
            label = course.name()
            instr = course.instructors_str()
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
            course_history.append_row([semester, label, instr, enrl, campus, joint, meeting_times])
        self.artifacts.append(course_history)




