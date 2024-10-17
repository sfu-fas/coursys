from ..report import Report
from ..table import Table
from coredata.models import Unit
from grad.models import GradStudent, STATUS_ACTIVE
from grad.templatetags.getattribute import getattribute

class FASGradsReport(Report):
    title = "FAS Grads TA Funding"
    description = "A report of all active FAS Grads with their Supervisors and TA Funding per year"

    def run(self):
        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE', 'APSC'])
    
        grads = GradStudent.objects.filter(program__unit__in=units, current_status__in=STATUS_ACTIVE).select_related('person', 'program').distinct()

        results = Table()
        results.append_column('Name')
        results.append_column('SFU ID')
        results.append_column('Program Unit')
        results.append_column('Program')
        results.append_column('Status')
        results.append_column('Start Semester')
        results.append_column('Senior Supervisors')
        results.append_column('Year 1 Funding')
        results.append_column('Year 2 Funding')
        results.append_column('Year 3 Funding')
        results.append_column('Year 4 Funding')
        results.append_column('Other Years Funding')

        for grad in grads:
            received_amt = grad.get_receive_all(type='ta')
            results.append_row([grad.person.name(), grad.person.emplid, grad.program.unit.label, grad.program.label, grad.current_status, grad.start_semester, getattribute(grad, 'senior_supervisors'), round(received_amt['year1'],2), round(received_amt['year2'],2), round(received_amt['year3'],2), round(received_amt['year4'],2), round(received_amt['otheryear'],2)])

        self.artifacts.append(results)