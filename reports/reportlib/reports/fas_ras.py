from ..report import Report
from ..table import Table
from coredata.models import Unit, Semester
from ra.models import RARequest
from decimal import Decimal
from django.db.models import Sum

class FASRACountsReport(Report):
    title = "FAS RA Counts"
    description = "A report that provides a count and funding total of all RA appointment types in FAS that began in the previous semester"

    def total_funding(self,queryset):
        total = queryset.aggregate(total=Sum("total_pay"))["total"] or Decimal("0.00")
        return total.quantize(Decimal("0.01"))

    def run(self):
        units = Unit.objects.filter(label__in=['CMPT', 'MSE', 'ENSC', 'SEE', 'APSC'])
        start, end = Semester.start_end_dates(Semester.current().offset(-1))
        results = Table()
        results.append_column('Unit')
        results.append_column('Research Assistant Total Count')
        results.append_column('Research Assistant (USRA) Total Count')
        results.append_column('Graduate Research Assistant Scholarship Total Count')
        results.append_column('Non-Continuing Research Assistant Total Count')
        results.append_column('Research Assistant Total Funding')
        results.append_column('Research Assistant (USRA) Funding')
        results.append_column('Graduate Research Assistant Scholarship Funding')
        results.append_column('Non-Continuing Research Assistant Funding')

        ras = RARequest.objects.filter(complete=True, deleted=False, draft=False, start_date__gte=start, start_date__lte=end)

        for unit in units:
            unit_ras = ras.filter(unit=unit)
            research_assistants = unit_ras.filter(hiring_category="RA", config__contains='"usra": false').distinct()
            research_assistant_usras = unit_ras.filter(hiring_category="RA", config__contains='"usra": true').distinct()
            graduate_research_assistants = unit_ras.filter(hiring_category="GRAS").distinct()
            non_continuings = unit_ras.filter(hiring_category="NC").distinct()
            
            total_research_assistant_count = research_assistants.count()
            total_research_assistant_usra_count = research_assistant_usras.count()
            total_graduate_research_assistant_count = graduate_research_assistants.count()
            total_non_continuing_count = non_continuings.count()

            total_research_assistant_funding = self.total_funding(research_assistants)
            total_research_assistant_usra_funding = self.total_funding(research_assistant_usras)
            total_graduate_research_assistant_funding = self.total_funding(graduate_research_assistants)
            total_non_continuing_funding = self.total_funding(non_continuings)
            results.append_row([str(unit), total_research_assistant_count, total_research_assistant_usra_count, total_graduate_research_assistant_count, total_non_continuing_count, total_research_assistant_funding, total_research_assistant_usra_funding, total_graduate_research_assistant_funding, total_non_continuing_funding])
        research_assistants = ras.filter(hiring_category="RA", config__contains='"usra": false').distinct()
        research_assistant_usras = ras.filter(hiring_category="RA", config__contains='"usra": true').distinct()
        graduate_research_assistants = ras.filter(hiring_category="GRAS").distinct()
        non_continuings = ras.filter(hiring_category="NC").distinct()
        
        total_research_assistant_count = research_assistants.count()
        total_research_assistant_usra_count = research_assistant_usras.count()
        total_graduate_research_assistant_count = graduate_research_assistants.count()
        total_non_continuing_count = non_continuings.count()

        total_research_assistant_funding = self.total_funding(research_assistants)
        total_research_assistant_usra_funding = self.total_funding(research_assistant_usras)
        total_graduate_research_assistant_funding = self.total_funding(graduate_research_assistants)
        total_non_continuing_funding = self.total_funding(non_continuings)
        results.append_row(["- ALL UNITS -", total_research_assistant_count, total_research_assistant_usra_count, total_graduate_research_assistant_count, total_non_continuing_count, total_research_assistant_funding, total_research_assistant_usra_funding, total_graduate_research_assistant_funding, total_non_continuing_funding])

        self.artifacts.append(results)
