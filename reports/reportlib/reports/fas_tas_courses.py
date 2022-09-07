from ..report import Report
from ..table import Table
from coredata.models import Semester, Unit
from ta.models import TACourse as ta_courses
from tacontracts.models import TACourse as tacontracts_courses

class FASTACoursesReport(Report):
    title = "FAS TAs and Courses for the Current Semester"
    description = "A report of all signed FAS TA contracts with courses in the current semester"

    def run(self):
        semester = Semester.current()
        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE', 'APSC'])
        
        # - /ta
        tas = ta_courses.objects.filter(contract__posting__semester=semester, 
                                        contract__status='SGN',
                                        contract__posting__unit__in=units)
        # - /tacontracts
        tacontracts = tacontracts_courses.objects.filter(contract__category__hiring_semester__semester=semester, 
                                                         contract__status='SGN',
                                                         contract__category__hiring_semester__unit__in=units)

        results = Table()
        results.append_column('Name')
        results.append_column('SFU ID')
        results.append_column('Course(s)')

        for ta in tas:
            results.append_row([ta.contract.application.person.sortname(), ta.contract.application.person.emplid, ta.course.name()])

        for ta in tacontracts:
            results.append_row([ta.contract.person.sortname(), ta.contract.person.emplid, ta.course.name()])

        results = results.flatten('SFU ID')

        self.artifacts.append(results)
