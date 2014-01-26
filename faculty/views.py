from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from courselib.search import find_userid_or_emplid

from coredata.models import Person, Unit, Role, Member, CourseOffering
from grad.models import Supervisor
from ra.models import RAAppointment

from faculty.models import CareerEvent
from faculty.forms import career_event_factory
from faculty.forms import CareerEventForm


def _get_faculty_role_or_404(allowed_units, userid_or_emplid):
    """
    Get the Role[role=~"faculty"] if we're allowed to see it, or raise Http404.
    """
    sub_unit_ids = Unit.sub_unit_ids(allowed_units)
    person = get_object_or_404(Person, find_userid_or_emplid(userid_or_emplid))
    role = get_object_or_404(Role, role='FAC', unit__id__in=sub_unit_ids, person=person)
    return role


###############################################################################
# Top-level views (management, etc. Not specific to a faculty member)

@requires_role('ADMN')
def index(request):
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    fac_roles = Role.objects.filter(role='FAC', unit__id__in=sub_unit_ids).select_related('person', 'unit')

    context = {
        'fac_roles': fac_roles,
    }
    return render(request, 'faculty/index.html', context)



###############################################################################
# Display/summary views for a faculty member

@requires_role('ADMN')
def summary(request, userid):
    """
    Summary page for a faculty member.
    """
    role = _get_faculty_role_or_404(request.units, userid)
    context = {
        'role': role,
        'person': role.person,
    }
    return render(request, 'faculty/summary.html', context)

@requires_role('ADMN')
def otherinfo(request, userid):
    role = _get_faculty_role_or_404(request.units, userid)

    # collect teaching history
    instructed = Member.objects.filter(role='INST', person=role.person, added_reason='AUTO') \
            .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
            .select_related('offering', 'offering__semester')

    # collect grad students
    supervised = Supervisor.objects.filter(supervisor=role.person, supervisor_type__in=['SEN','COS','COM'], removed=False) \
            .select_related('student', 'student__person', 'student__program', 'student__start_semester', 'student__end_semester')


    # RA appointments supervised
    ras = RAAppointment.objects.filter(deleted=False, hiring_faculty=role.person) \
            .select_related('person', 'project', 'account')

    context = {
        'person': role.person,
        'role': role,
        'instructed': instructed,
        'supervised': supervised,
        'ras': ras,
    }
    return render(request, 'faculty/otherinfo.html', context)



###############################################################################
# Creation and editing of CareerEvents
@requires_role('ADMN')
def create_event(request, userid):
    """
    Create new career event for a faculty member.
    """
    role = _get_faculty_role_or_404(request.units, userid)
    person = role.person
    context = {"role": role, "person": person}
    if request.method == "POST":
        form = CareerEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.person = person
            event.save()
            return HttpResponseRedirect(event.get_change_url())
        else:
            context.update({"event_form": form})
    else:
        unit_choices = [(u.id, unicode(u)) for u in request.units]
        form = CareerEventForm(initial={"person": person, "status": "NA"})
        form.fields['unit'].choices = unit_choices
        # TODO filter choice for status (some roles may not be allowed to approve events?
        context.update({"event_form": form})
    return render(request, 'faculty/career_event.html', context)


@requires_role('ADMN')
def change_event(request, userid, slug):
    """
    Change existing career event for a faculty member.
    """
    role = _get_faculty_role_or_404(request.units, userid)
    person = role.person
    instance = get_object_or_404(CareerEvent, slug=slug, person=person)
    context = {"role": role, "person": person, "event": instance}
    if request.method == "POST":
        pass
    else:
        unit_choices = [(u.id, unicode(u)) for u in request.units]
        form = CareerEventForm(instance=instance)
        form.fields['unit'].choices = unit_choices
        # TODO filter choice for status (as above)
        context.update({"event_form": form})
    return render(request, 'faculty/career_event.html', context)


###############################################################################
# Management of DocumentAttachments and Memos



