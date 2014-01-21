from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from courselib.search import find_userid_or_emplid

from coredata.models import Person, Unit, Role, Member, CourseOffering
from grad.models import Supervisor
from ra.models import RAAppointment


def _get_faculty_role_or_404(allowed_units, unit_slug, userid_or_emplid):
    """
    Get the Role[role=~"faculty"] if we're allowed to see it, or raise Http404.
    """
    sub_unit_ids = Unit.sub_unit_ids(allowed_units)
    person = get_object_or_404(Person, find_userid_or_emplid(userid_or_emplid))
    role = get_object_or_404(Role, role='FAC', unit__id__in=sub_unit_ids, unit__slug=unit_slug, person=person)
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
def summary(request, unit_slug, userid):
    """
    Summary page for a faculty member.
    """
    role = _get_faculty_role_or_404(request.units, unit_slug, userid)
    context = {
        'role': role,
    }
    return render(request, 'faculty/summary.html', context)

@requires_role('ADMN')
def otherinfo(request, unit_slug, userid):
    role = _get_faculty_role_or_404(request.units, unit_slug, userid)

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



###############################################################################
# Management of DocumentAttachments and Memos



