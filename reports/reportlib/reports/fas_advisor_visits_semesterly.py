from ..report import Report
from ..table import Table
from ..semester import current_semester, previous_semester
from advisornotes.models import AdvisorVisit
from coredata.models import Unit
from datetime import datetime, timedelta

class FASAdvisorVisitsSemesterlyReport(Report):
    title = "FAS Advisor Visit Semesterly Report"
    description = "A report of all advisor visits for the previous semester"

    def run(self):
        #  Previous to this early_cutoff, there is data that is irrelevant to us.
        early_cutoff = datetime(2019, 3, 8)
        start = previous_semester().start_date()
        end = current_semester().start_date()
        fasunit = Unit.objects.get(label='APSC')
        visits = AdvisorVisit.objects.visible([fasunit]).filter(created_at__gte=start)\
            .exclude(created_at__lte=early_cutoff).exclude(created_at__gte=end)\
            .select_related('student', 'nonstudent', 'advisor',).prefetch_related('categories').order_by("-created_at")
        results = Table()
        results.append_column('Start')
        results.append_column('End')
        results.append_column('Duration')
        results.append_column('Mode')
        results.append_column('Campus')
        results.append_column('Student')
        results.append_column('Advisor')
        results.append_column('Categories')
        results.append_column('Programs')
        results.append_column('CGPA')
        results.append_column('Credits')
        results.append_column('Gender')
        results.append_column('Citizenship')

        for v in visits:
            results.append_row(
                [v.get_created_at_display(), v.get_end_time_display(), v.get_duration(), v.get_mode_display(), v.get_campus_display(),
                 v.get_full_name(), v.advisor.sortname_pref_only(), v.categories_display(), v.programs, v.cgpa, v.credits,
                 v.gender, v.citizenship])
        self.artifacts.append(results)
