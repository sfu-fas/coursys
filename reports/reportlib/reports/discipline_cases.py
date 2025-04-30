from ..report import Report
from ..table import Table
from discipline.models import DisciplineCaseBase
from coredata.models import Semester, CourseOffering

class DisciplineReport(Report):
    title = "Discipline Report"
    description = "A report of all discipline cases for offerings in the last complete year"

    def run(self):
        results = Table()
        results.append_column('Student Name')
        results.append_column('Student Number') 
        results.append_column('Course Subject')
        results.append_column('Course Number')
        results.append_column('Course Section')
        results.append_column('Semester')
        results.append_column('Delivery')
        results.append_column('Penalty')
        results.append_column('Weight of Assignment') 
        results.append_column('Referred to Chair')
        results.append_column('Contact Date')
        results.append_column('Letter Date')
        results.append_column('Part of Cluster')
        results.append_column('Case Creator')

        start_semester = Semester.current().offset(-4)
        end_semester = Semester.current().offset(-1)

        cases = DisciplineCaseBase.objects.filter(offering__semester__gte=start_semester, offering__semester__lte=end_semester)

        for c in cases:
            # student info
            subcase = c.subclass()
            name = subcase.student.name()
            emplid = str(subcase.student.emplid)
            
            # course offering info
            co = c.offering
            subject = co.subject
            number = co.number
            section = co.section

            # semester info
            sem = co.semester
            semester = str(sem.name) + " (" + str(sem) + ")"

            # case info
            if 'mode' in c.config:
                mode = c.config['mode']
            else:
                mode = ''
            penalty = c.get_penalty_display()
            sem = co.semester
            if 'weight' in c.config:
                weight = c.config['weight']
            else:
                weight = ''
            refer = "Y" if c.refer else "N"
            contact_date = str(c.contact_date) if c.contact_date else ""
            letter_date = str(c.letter_date) if c.letter_date else ""
            group = "Y" if subcase.group else "N"
            creator = str(c.owner)
            results.append_row([name, emplid, subject, number, section, semester, mode, penalty, weight, refer, contact_date, letter_date, group, creator])
            
        self.artifacts.append(results)

