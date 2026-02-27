from ..report import Report
from ..table import Table
from coredata.models import Unit
from grad.models import GradStudent, GradProgram

class FASGradStatusCountsReport(Report):
    title = "FAS Grad Student Status Counts"
    description = "A report that provides a count of each group of grad students in FAS by their grad status (e.g. active, completed, etc.)"

    def run(self):
        # previous 5 years
        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE'])
        results = Table()
        results.append_column('Unit')
        results.append_column('Program')
        results.append_column('Active')
        results.append_column('Deferred')
        results.append_column('On-Leave')

        for unit in units:
            grad_programs = GradProgram.objects.filter(unit=unit).order_by('label')
            total_active_count = GradStudent.objects.filter(program__unit=unit, current_status="ACTI").distinct().count()
            total_deferred_count = GradStudent.objects.filter(program__unit=unit, current_status="DEFR").distinct().count()
            total_on_leave_count = GradStudent.objects.filter(program__unit=unit, current_status="LEAV").distinct().count()
            results.append_row([str(unit), "- ALL PROGRAMS -", total_active_count, total_deferred_count, total_on_leave_count])
            for grad_program in grad_programs:
                active_count = GradStudent.objects.filter(program=grad_program, current_status="ACTI").distinct().count()
                deferred_count = GradStudent.objects.filter(program=grad_program, current_status="DEFR").distinct().count()
                on_leave_count = GradStudent.objects.filter(program=grad_program, current_status="LEAV").distinct().count()
                if not (active_count == 0 and deferred_count == 0 and on_leave_count == 0):
                    results.append_row([str(unit), str(grad_program), active_count, deferred_count, on_leave_count])
        
        total_active_count = GradStudent.objects.filter(program__unit__in=units, current_status="ACTI").distinct().count()
        total_deferred_count = GradStudent.objects.filter(program__unit__in=units, current_status="DEFR").distinct().count()
        total_on_leave_count = GradStudent.objects.filter(program__unit__in=units, current_status="LEAV").distinct().count()
        results.append_row(["- ALL UNITS -", "- ALL PROGRAMS -", total_active_count, total_deferred_count, total_on_leave_count])
        
        self.artifacts.append(results)
