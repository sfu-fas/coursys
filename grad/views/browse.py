from courselib.auth import requires_role
from django.shortcuts import render
from django.utils.html import escape
from grad.models import GradStudent, GradProgram, Supervisor
from grad.forms import GradFilterForm
from coredata.models import Unit, Semester, Person
from django_datatables_view.base_datatable_view import BaseDatatableView
from haystack.query import SearchQuerySet
import ast

@requires_role("GRAD")
def browse(request):
    if 'tabledata' in request.GET:
        return GradDataJson.as_view()(request)
    units = Unit.sub_units(request.units)
    programs = GradProgram.objects.filter(unit__in=request.units)
    form = GradFilterForm(units, programs)
    context = {'form': form}
    return render(request, 'grad/browse.html', context)

class GradDataJson(BaseDatatableView):
    model = GradStudent
    columns = ['person', 'emplid', 'program', 'start_semester', 'completion_progress', 'supervisor', 'status']
    order_columns = [
        ['person__last_name', 'person__first_name'],
        'person__emplid',
        'program',
        'start_semester',
        'completion_progress',
        'supervisor',
        'status'
    ]
    max_display_length = 500

    def get_initial_queryset(self):
        qs = super(GradDataJson, self).get_initial_queryset()
        qs = qs.select_related('program')
        return qs

    def filter_queryset(self, qs):
        GET = self.request.GET

        # search box
        srch = GET.get('sSearch', None)
        if srch:
            grad_qs = SearchQuerySet().models(GradStudent).filter(text__fuzzy=srch)[:500]
            grad_qs = [r for r in grad_qs if r is not None]
            if grad_qs:
                max_score = max(r.score for r in grad_qs)
                grad_pks = (r.pk for r in grad_qs if r.score > max_score/5)
                qs = qs.filter(id__in=grad_pks)
            else:
                qs = qs.none()
        
        unit = GET.get('unit', None)
        if unit:
            unit = Unit.objects.get(label=unit)
            qs = qs.filter(program__unit=unit)

        program = GET.get('program', None)
        if program:
            program = ast.literal_eval(program)
            unit = Unit.objects.get(label=program[1])
            program = GradProgram.objects.get(label=program[0], unit=unit)
            qs = qs.filter(program=program)

        started_by = GET.get('started_by', None)
        if started_by:
            semester = Semester.objects.get(name=started_by)
            qs = qs.filter(start_semester__gte=semester)

        supervisor = GET.get('supervisor', None)
        if supervisor:
            qs = qs.filter()

        status = GET.get('status', None)
        if status:
            qs = qs.filter(current_status=status)
        
        return qs

    def render_column(self, grad, column):
        if column == 'person':
            url = grad.get_absolute_url()
            name = grad.person.sortname()
            return '<a href="%s">%s</a>' % (escape(url), escape(name))
        elif column == 'emplid':
            return grad.person.emplid
        elif column == 'program':
            return grad.program.unit.label + ", " + grad.program.label
        elif column == 'start_semester':
            return grad.start_semester.name + " (" + grad.start_semester.label() + ")"
        elif column == 'completion_progress':
            active_semesters = grad.active_semesters()[0]
            return str(active_semesters) + "/" + str(grad.program.expected_completion_terms)
        elif column == 'supervisor':
            return grad.list_supervisors()
        elif column == 'status':
            return grad.get_current_status_display()

        return str(getattr(grad, column))