from reports.reportlib import Table
from ..report import Report
from coredata.models import CourseOffering, Unit, Semester


class FASOfferingsReport(Report):
    title = "Course offering summary for FAS"
    description = "Course offering summary for FAS"

    def run(self):
        results = Table()
        results.append_column('Course')
        results.append_column('Semester')
        results.append_column('Owner')
        results.append_column('Type')
        results.append_column('Units')

        start_semester = Semester.current().offset(-15)
        fas = Unit.objects.get(label='APSC')
        units = Unit.sub_units([fas])
        offerings = CourseOffering.objects \
            .filter(owner__in=units, graded=True, semester__name__gte=start_semester.name) \
            .exclude(flags=CourseOffering.flags.combined) \
            .select_related('semester', 'owner')

        for o in offerings:
            results.append_row([o.name(), o.semester.name, o.owner.label, o.get_component_display(), o.units])

        self.artifacts.append(results)
