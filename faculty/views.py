from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from courselib.search import find_userid_or_emplid

from coredata.models import Person, Unit, Role, Member
from grad.models import Supervisor
from ra.models import RAAppointment

@requires_role('ADMN')
def index(request):
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    fac_roles = Role.objects.filter(role='FAC', unit__id__in=sub_unit_ids).select_related('person')

    context = {
        'fac_roles': fac_roles,
    }
    return render(request, 'faculty/index.html', context)


@requires_role('ADMN')
def summary(request, userid):
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    person = get_object_or_404(Person, find_userid_or_emplid(userid))
    role = get_object_or_404(Role, role='FAC', unit__id__in=sub_unit_ids, person=person)

    # collect teaching history
    instructed = Member.objects.filter(role='INST', person=person, added_reason='AUTO').exclude(offering__component='CAN') \
            .select_related('offering', 'offering__semester')

    # collect grad students
    supervised = Supervisor.objects.filter(supervisor=person, supervisor_type__in=['SEN','COS','COM'], removed=False) \
            .select_related('student', 'student__person', 'student__program', 'student__start_semester', 'student__end_semester')


    # RA appointments supervised
    ras = RAAppointment.objects.filter(deleted=False, hiring_faculty=person) \
            .select_related('person', 'project', 'account')

    context = {
        'person': person,
        'role': role,
        'instructed': instructed,
        'supervised': supervised,
        'ras': ras,
    }
    return render(request, 'faculty/summary.html', context)
