from ..report import Report
from ..table import Table
from coredata.models import Unit
from grad.models import GradStudent, GradProgram

class FASGradStatusCountsReport(Report):
    title = "FAS Grad Student Status Counts"
    description = "A report that provides a count of each group of grad students in FAS by their grad status, domestic and international"

    def run(self):
        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE'])
        results = Table()
        results.append_column('Unit')
        results.append_column('Program')
        results.append_column('Active (Domestic)')
        results.append_column('Deferred (Domestic)')
        results.append_column('On-Leave (Domestic)')
        results.append_column('Active (International)')
        results.append_column('Deferred (International)')
        results.append_column('On-Leave (International)')

        for unit in units:
            grad_programs = GradProgram.objects.filter(unit=unit).order_by('label')
            total_active_count_domestic = GradStudent.objects.filter(program__unit=unit, current_status="ACTI", is_canadian=True).distinct().count()
            total_deferred_count_domestic = GradStudent.objects.filter(program__unit=unit, current_status="DEFR", is_canadian=True).distinct().count()
            total_on_leave_count_domestic = GradStudent.objects.filter(program__unit=unit, current_status="LEAV", is_canadian=True).distinct().count()
            total_active_count_international = GradStudent.objects.filter(program__unit=unit, current_status="ACTI", is_canadian=False).distinct().count()
            total_deferred_count_international = GradStudent.objects.filter(program__unit=unit, current_status="DEFR", is_canadian=False).distinct().count()
            total_on_leave_count_international = GradStudent.objects.filter(program__unit=unit, current_status="LEAV", is_canadian=False).distinct().count()
            results.append_row([str(unit), "- ALL PROGRAMS -", total_active_count_domestic, total_deferred_count_domestic, total_on_leave_count_domestic, total_active_count_international, total_deferred_count_international, total_on_leave_count_international])
            for grad_program in grad_programs:
                active_count_domestic = GradStudent.objects.filter(program=grad_program, current_status="ACTI", is_canadian=True).distinct().count()
                deferred_count_domestic = GradStudent.objects.filter(program=grad_program, current_status="DEFR", is_canadian=True).distinct().count()
                on_leave_count_domestic = GradStudent.objects.filter(program=grad_program, current_status="LEAV", is_canadian=True).distinct().count()
                active_count_international = GradStudent.objects.filter(program=grad_program, current_status="ACTI", is_canadian=False).distinct().count()
                deferred_count_international = GradStudent.objects.filter(program=grad_program, current_status="DEFR", is_canadian=False).distinct().count()
                on_leave_count_international = GradStudent.objects.filter(program=grad_program, current_status="LEAV", is_canadian=False).distinct().count()
                if not (active_count_domestic == 0 and deferred_count_domestic == 0 and on_leave_count_domestic == 0 and active_count_international == 0 and deferred_count_international == 0 and on_leave_count_international == 0):
                    results.append_row([str(unit), str(grad_program), active_count_domestic, deferred_count_domestic, on_leave_count_domestic, active_count_international, deferred_count_international, on_leave_count_international])

        total_active_count_domestic = GradStudent.objects.filter(program__unit__in=units, current_status="ACTI", is_canadian=True).distinct().count()
        total_deferred_count_domestic = GradStudent.objects.filter(program__unit__in=units, current_status="DEFR", is_canadian=True).distinct().count()
        total_on_leave_count_domestic = GradStudent.objects.filter(program__unit__in=units, current_status="LEAV", is_canadian=True).distinct().count()
        total_active_count_international = GradStudent.objects.filter(program__unit__in=units, current_status="ACTI", is_canadian=False).distinct().count()
        total_deferred_count_international = GradStudent.objects.filter(program__unit__in=units, current_status="DEFR", is_canadian=False).distinct().count()
        total_on_leave_count_international = GradStudent.objects.filter(program__unit__in=units, current_status="LEAV", is_canadian=False).distinct().count()
        results.append_row(["- ALL UNITS -", "- ALL PROGRAMS -", total_active_count_domestic, total_deferred_count_domestic, total_on_leave_count_domestic, total_active_count_international, total_deferred_count_international, total_on_leave_count_international])

        self.artifacts.append(results)
