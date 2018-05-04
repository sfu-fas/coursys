from reports.reportlib.report import Report
from reports.reportlib.table import Table
from coredata.models import Semester, Unit, CourseOffering, Member, Role
from faculty.models import CareerEvent
import itertools


class CourseTeachingByInstructorReport(Report):
    title = "Course Teaching by Instructor"
    description = "This report summarizes course information for FAS schools, including enrollment, instructors, etc"

    def run(self):
        sems = Semester.objects.filter(name__gte='1101', name__lte=Semester.current().name)
        u = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC'])
        courses = CourseOffering.objects.prefetch_related('meeting_time').filter(semester__in=sems, owner__in=u,
                                                                                 graded=True).exclude(
            flags=CourseOffering.flags.combined).exclude(subject='DDP').order_by('semester', 'subject', 'number')

        instructors = Member.objects.filter(role='INST', added_reason='AUTO', offering__in=courses) \
            .exclude(offering__component='CAN') \
            .order_by('person__last_name', 'person__first_name', 'offering__semester__name')

        course_history = Table()
        course_history.append_column('Instructor')
        course_history.append_column('First Teaching Semester (>=1101)')
        course_history.append_column('Last Teaching Semester')
        course_history.append_column('Current Rank')
        course_history.append_column('School')
        course_history.append_column('Teaching Credits')
        course_history.append_column('Mean Headcount')
        course_history.append_column('Crs per Year')
        course_history.append_column('Crs Levels')

        for i, memberships in itertools.groupby(instructors, key=lambda i: i.person):
            memberships = [m for m in memberships if m.teaching_credit() > 0]
            if i is None or not memberships:
                continue

            instr = i.sortname()
            first_semester = memberships[0].offering.semester
            last_semester = memberships[-1].offering.semester
            rank = CareerEvent.current_ranks(i.id)
            roles = Role.objects.filter(person=i, role='FAC').select_related('unit')
            unit = ', '.join(r.unit.label for r in roles)

            if rank == 'unknown' or unit == '':
                continue

            offerings = [m.offering for m in memberships]
            num_offerings = float(sum(m.teaching_credit() for m in memberships))
            headcount = sum(o.enrl_tot for o in offerings)
            duration = last_semester - first_semester + 1
            levels = sorted(list(set(str(o.number)[0] for o in offerings)))

            course_history.append_row([instr, first_semester.name, last_semester.name, rank, unit, round(num_offerings, 1),
                                       round(headcount/num_offerings, 1), round(num_offerings/duration*3, 1),
                                       ','.join(levels)])

        self.artifacts.append(course_history)
