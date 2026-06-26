from courselib.celerytasks import task
from django.conf import settings
from reports.models import Report, schedule_ping


@task()
def run_regular_reports():
    if not settings.DO_IMPORTING_HERE:
        return
    schedule_ping()


@task(queue='sims')
def run_report(report_id, manual):
    report = Report.objects.get(id=report_id)
    # TODO: what if the report takes longer than the max task running time?
    # Should break up each HardcodedReport and Query into separate tasks?
    report.run(manual=manual)