from ..report import Report
from ..table import Table
from coredata.models import Semester, Unit
from ta.models import TACourse as ta_course, TAContract as ta_contract
from tacontracts.models import TAContract as tacontracts_contract
from visas.models import Visa
from django.db.models import Q
from django.urls import reverse
from django.conf import settings

class FASTAHistoryReport(Report):
    title = "FAS TA History Report"
    description = "A report of all signed or accepted TA contracts from the past 5 years, with approximate Visa status at the time of appointment start date"

    def get_visa_info(self, student, start_date):
        visa_type, visa_start_date, visa_end_date = "", "", ""
        visa = Visa.objects.filter(person=student, start_date__lte=start_date, hidden=False).order_by('-start_date').filter(Q(end_date__gte=start_date) | Q(end_date__isnull=True)).order_by('-start_date').first()
        if visa:
            visa_type = visa.status
            visa_start_date = visa.start_date or "Unspecified"
            visa_end_date = visa.end_date or "Unspecified"
        return visa_type, visa_start_date, visa_end_date

    def run(self):
        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE', 'APSC'])
        start_semester = Semester.current().offset(-15)
        
        # /ta
        tas = ta_contract.objects.filter(posting__semester__gte=start_semester, 
                                        status__in=['SGN', 'ACC'],
                                        posting__unit__in=units)
        # /tacontracts
        tacontracts = tacontracts_contract.objects.filter(category__hiring_semester__semester__gte=start_semester, 
                                                         status__in=['SGN'],
                                                         category__hiring_semester__unit__in=units)

        results = Table()
        results.append_column('Semester')
        results.append_column('Unit')
        results.append_column('TA Name')
        results.append_column('TA ID')
        results.append_column('Category')
        results.append_column('Appointment Start Date')
        results.append_column('Appointment End Date')
        results.append_column('Course(s)')
        results.append_column('Number of BUs')
        results.append_column('Contract Status')
        results.append_column('Source')
        results.append_column('Visa Type')
        results.append_column('Visa Start Date')
        results.append_column('Visa End Date')

        for ta in tas:
            # contract info
            semester = ta.posting.semester.name
            unit = ta.posting.unit.label
            name = ta.application.person.sortname()
            id = ta.application.person.emplid
            category = str(ta.appt_category) + " " + ta.get_appt_category_display() + " - " + str(ta.position_number)
            start_date = ta.appointment_start
            end_date = ta.appointment_end
            courses = ''
            ta_courses = ta_course.objects.filter(contract=ta)
            if len(ta_courses) > 0:
                courses = ', '.join([tacourse.course.name() for tacourse in ta_courses])
            total_bu = ta.total_bu()
            status = "Signed" if ta.status == 'SGN' else "Accepted"
            source = settings.BASE_ABS_URL + reverse('ta:view_application', kwargs={'post_slug': ta.application.posting.slug, 'userid': ta.application.person.userid})

            # visa info
            visa_type, visa_start_date, visa_end_date = self.get_visa_info(ta.application.person, ta.appointment_start)
           
            results.append_row([semester, unit, name, id, category, start_date, end_date, courses, total_bu, status, source, visa_type, visa_start_date, visa_end_date])

        for ta in tacontracts:
            # contract info
            semester = ta.category.hiring_semester.semester.name
            unit = ta.category.hiring_semester.unit.label
            name = ta.person.sortname()
            id = ta.person.emplid
            category = str(ta.category.code) + " " + str(ta.category.title) + " - " + str(ta.category.account)
            start_date = ta.appointment_start
            end_date = ta.appointment_end
            courses = ta.course_list_string()
            total_bu = ta.total_bu
            status = "Signed"
            source = settings.BASE_ABS_URL + reverse('tacontracts:view_contract', kwargs={'unit_slug': ta.category.hiring_semester.unit.label, 'semester': ta.category.hiring_semester.semester.name, 'contract_slug': ta.slug})

            # visa info
            visa_type, visa_start_date, visa_end_date = self.get_visa_info(ta.person, ta.appointment_start)

            results.append_row([semester, unit, name, id, category, start_date, end_date, courses, total_bu, status, source, visa_type, visa_start_date, visa_end_date])

        self.artifacts.append(results)
