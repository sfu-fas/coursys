from ..report import Report
from ..table import Table
from coredata.models import Unit
from grad.models import GradStudent, Supervisor, STATUS_ACTIVE

class FASSupervisorReport(Report):
    title = "FAS Supervisors of Active Grad Students"
    description = "A report of all internal supervisors and their active grad students within FAS"

    def run(self):
        results = Table()
        results.append_column('Supervisor Name')
        results.append_column('Supervisor Emplid')
        results.append_column('Supervisor Email')
        results.append_column('Supervisor Type')
        results.append_column('Student Name')
        results.append_column('Student ID')
        results.append_column('Student Email')
        results.append_column('Student Unit')
        results.append_column('Student Program')
        results.append_column('Student Status')
        results.append_column('Student Start Semester')

        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE', 'APSC'])
        
        # find ids of active grads with supervisors
        grads = GradStudent.objects.filter(current_status__in=STATUS_ACTIVE, program__unit__in=units)
        grad_ids = [grad.id for grad in grads if grad.has_supervisor(include_potential=True)]

        # find the supervisors of these students
        supervisors = Supervisor.objects.filter(student__id__in=grad_ids, supervisor_type__in=['SEN', 'COM', 'COS', 'POT'], removed=False).order_by('supervisor__last_name', 'supervisor__first_name', 'supervisor_type').select_related('student').select_related('supervisor')

        for s in supervisors:
            student = s.student
            student_start_semester = "%s (%s)" % (student.start_semester.name, student.start_semester.label()) 
            if s.supervisor:
                results.append_row([s.supervisor.sortname(), str(s.supervisor.emplid), str(s.supervisor.email()), s.get_supervisor_type_display(), student.person.sortname(), str(student.person.emplid), str(student.person.email()), student.program.unit.label, student.program.label, student.get_current_status_display(), student_start_semester])

        self.artifacts.append(results)
