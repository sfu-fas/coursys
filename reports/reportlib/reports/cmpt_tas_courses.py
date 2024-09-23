from ..report import Report
from ..table import Table
from coredata.models import Semester, Unit
from ta.models import TACourse as ta_courses
from tacontracts.models import TACourse as tacontracts_courses

class CMPTTACoursesReport(Report):
    title = "CMPT TAs and Courses for the Current Semester"
    description = "A report of all accepted/signed CMPT TA contracts with courses in the current semester"
    
    def run(self):
        semester = Semester.current()
        units = Unit.objects.filter(label__in=['CMPT'])
        
        # - /ta
        tas = ta_courses.objects.filter(contract__posting__semester=semester, 
                                        contract__status__in=['SGN', 'ACC'],
                                        contract__posting__unit__in=units).order_by("course__name", "contract__application__person__emplid")
        # - /tacontracts
        tacontracts = tacontracts_courses.objects.filter(contract__category__hiring_semester__semester=semester, 
                                                         contract__status='SGN',
                                                         contract__category__hiring_semester__unit__in=units).order_by("course__name")

        results = Table()
        results.append_column('Name of TA')
        results.append_column('SFU ID')
        results.append_column('User ID')
        results.append_column('Course Number')
        results.append_column('Course Maillist')
        results.append_column('Course Name')
        results.append_column('Instructor UserID(s)')

        for ta in tas:
            results.append_row([ta.contract.application.person.name_with_pref(), ta.contract.application.person.emplid, ta.contract.application.person.userid, ta.course.name(), ta.course.maillist(), ta.course.title, "; ".join(p.userid for p in ta.course.instructors())])

        for ta in tacontracts:
            results.append_row([ta.contract.person.name_with_pref(), ta.contract.person.emplid, ta.contract.person.userid, ta.course.name(), ta.course.maillist(), ta.course.title, "; ".join(p.userid for p in ta.course.instructors())])

        self.artifacts.append(results)
