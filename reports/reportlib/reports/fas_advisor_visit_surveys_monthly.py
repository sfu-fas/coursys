from ..report import Report
from ..table import Table
from advisornotes.models import AdvisorVisitSurvey
from advisornotes.views import SURVEY_UNITS
from coredata.models import Unit
from datetime import date

class FASAdvisorVisitSurveyMonthlyReport(Report):
    title = "FAS Advisor Visit Survey Monthly Report"
    description = "A report of all students who submitted surveys in the last calendar month"

    def run(self):
        units = Unit.objects.filter(label__in=SURVEY_UNITS)
        today = date.today()
        end_date = today.replace(day=1) # first day of this month
        if end_date.month == 1: # adjust year if dec/jan
            start_date = end_date.replace(year=end_date.year-1, month=12)
        else:
            start_date = end_date.replace(month=end_date.month-1)

        surveys = AdvisorVisitSurvey.objects.filter(visit__unit__in=units, completed_at__gte=start_date, completed_at__lt=end_date).exclude(visit__isnull=True, completed_at__isnull=True).order_by("completed_at")

        results = Table()
        results.append_column('Survey Completed At')
        results.append_column('Student Name')
        results.append_column('Student Email')

        for s in surveys:
            results.append_row([s.completed_at.strftime("%Y/%m/%d %H:%M"), s.visit.get_full_name(), s.visit.get_email()])
        self.artifacts.append(results)
