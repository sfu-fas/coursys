from django.core.management.base import BaseCommand
from grad.models import GradStudent, CompletedRequirement, Letter, Scholarship, OtherFunding, Promise, FinancialComment, GradFlagValue, ProgressReport, ExternalDocument

class Command(BaseCommand):
    def handle(self, *args, **options):
        unit_slugs = args
        gss = GradStudent.objects.filter(program__unit__slug__in=unit_slugs)
        gs_ids = [gs.id for gs in gss]

        for Model in [CompletedRequirement, Letter, Scholarship, OtherFunding, Promise, FinancialComment, GradFlagValue, ProgressReport, ExternalDocument]:
            print(Model.objects.filter(student_id__in=gs_ids))