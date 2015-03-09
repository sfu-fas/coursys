from django.core.management.base import BaseCommand
from django.core import serializers

from coredata.models import Unit, Person, Semester, Role
from grad.models import GradProgram, GradStudent, GradProgramHistory, Supervisor, \
    GradStatus, ProgressReport

class Command(BaseCommand):
    def handle(self, *args, **options):
        unit_slugs = args
        units = Unit.objects.filter(slug__in=unit_slugs)

        objs = list(units)
        objs.extend(Semester.objects.all())

        for unit in units:
            objs.extend(unit.super_units())
            objs.extend(GradProgram.objects.filter(unit=unit))
            gss = GradStudent.objects.filter(program__unit=unit).select_related('person')
            objs.extend(gss)
            objs.extend(GradProgramHistory.objects.filter(program__unit=unit))
            supervs = Supervisor.objects.filter(student__program__unit=unit).select_related('supervisor')
            objs.extend(supervs)
            objs.extend(GradStatus.objects.filter(student__program__unit=unit))
            objs.extend(ProgressReport.objects.filter(student__program=unit))

            people = set(gs.person for gs in gss) \
                     | set(s.supervisor for s in supervs if s.supervisor) \
                     | set([Person.objects.get(userid='ggbaker')])

            objs.extend(people)
            objs.extend(Role.objects.filter(person__userid='ggbaker', unit=unit))

        data = serializers.serialize("json", objs, sort_keys=True, indent=1)
        print data


