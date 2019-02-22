from reports.reportlib.report import Report
from reports.reportlib.table import Table
from coredata.models import Semester, Unit, CourseOffering, CAMPUSES_SHORT, WEEKDAYS
from faculty.models import CareerEvent
from grad.models import Supervisor


class CourseHistoryByInstructorReport(Report):
    title = "Course History by Instructor"
    description = "This report summarizes course information for FAS schools, including enrollment, instructors, etc"

    def run(self):
        sems = Semester.objects.filter(name__gte='1094', name__lte=Semester.current().offset(2).name)
        u = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC'])
        courses = CourseOffering.objects.prefetch_related('meeting_time').filter(semester__in=sems, owner__in=u,
                                                                                 graded=True).exclude(
            flags=CourseOffering.flags.combined).exclude(subject='DDP').order_by('semester', 'subject', 'number')
        courses = list(courses)
        courses.sort(key=lambda x: (x.instructors_printing_str(), x.semester))
        course_history = Table()
        course_history.append_column('Instructor')
        course_history.append_column('Instructor(s) Rank(s)')
        course_history.append_column('School')
        course_history.append_column('Grad Students')
        course_history.append_column('Semester')
        course_history.append_column('Course')
        course_history.append_column('Enrolment')
        course_history.append_column('Campus')
        course_history.append_column('Joint With')
        course_history.append_column('Lecture Times')
        course_history.append_column('Credits')
        for course in courses:
            semester = course.semester.label()
            label = course.name()
            instr = course.instructors_printing_str()
            enrl = '%i/%i' % (course.enrl_tot, course.enrl_cap)
            unit = course.owner
            credits = course.units
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
            grads = "; ".join(str(Supervisor.objects.filter(supervisor__userid=p.userid, supervisor_type='SEN', removed=False).count()) for p in course.instructors())
            ranks = "; ".join(CareerEvent.ranks_as_of_semester(p.id, course.semester) for p in course.instructors())
            course_history.append_row([instr, ranks, unit, grads, semester, label, enrl, campus, joint, meeting_times, credits])
        self.artifacts.append(course_history)
