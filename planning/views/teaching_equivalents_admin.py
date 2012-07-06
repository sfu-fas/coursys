from coredata.models import Role, Member, Person
from courselib.auth import requires_role
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from planning.models import TeachingEquivalent
from planning.views.teaching_equivalents_inst import _get_teaching_credits_by_semester
from planning.teaching_equiv_forms import TeachingEquivForm
from django.contrib import messages
from django.core.urlresolvers import reverse

def _get_administrative_instructors(request):
    """
    Gets all instructors (person) that the teaching admin is responsible for
    """
    roles = Role.objects.filter(role='TADM', person__userid=request.user.username)
    role_units = [role.unit for role in roles]
    instructors = Member.objects.filter(role='INST', offering__owner__in=role_units)
    instructor_list = []
    for member in instructors:
        if not member.person in instructor_list:
            instructor_list.append(member.person)
    return instructor_list

def _get_instructor_for_units(request, userid):
    """
    Returns the instructor after validating that he/she exists and is within the teaching admininstrators role/units
    """
    instructor = get_object_or_404(Person, userid=userid)
    roles = Role.objects.filter(role='TADM', person__userid=request.user.username)
    role_units = [role.unit for role in roles]
    memberships = Member.objects.filter(role='INST', person__userid=userid, offering__owner__in=role_units)
    if len(memberships) is 0:
        raise Http404
    return instructor

@requires_role('TADM')
def view_insts_in_unit(request):
    """
    View that lists all instructors in teaching admins unit to administrate teaching equivalents
    """
    instructors = _get_administrative_instructors(request)
    return render(request, 'planning/teaching_credits_admin_index.html', {'instructors': instructors})

@requires_role('TADM')
def view_teaching_credits_admin(request, userid):
    """
    View teaching credits for an instructor
    """
    instructor = _get_instructor_for_units(request, userid)
    semesters = _get_teaching_credits_by_semester(instructor)
    return render(request, 'planning/view_teaching_credits_admin.html', {'semesters': semesters, 'instructor': instructor})

@requires_role('TADM')
def view_teaching_equivalent_admin(request, userid, equivalent_id):
    """
    View a teaching equivalent for an instructor
    """
    instructor = _get_instructor_for_units(request, userid)
    equivalent = get_object_or_404(TeachingEquivalent, pk=equivalent_id, instructor=instructor)
    return render(request, 'planning/view_teaching_equiv_admin.html', {'equivalent': equivalent, 'instructor': instructor})

@requires_role('TADM')
def new_teaching_equivalent_admin(request, userid):
    """
    Create a new teaching equivalent for an instructor
    """
    instructor = _get_instructor_for_units(request, userid)
    if request.method == 'POST':
        form = TeachingEquivForm(request.POST)
        if form.is_valid():
            equivalent = form.save(commit=False)
            equivalent.credits_numerator = form.cleaned_data['credits_numerator']
            equivalent.credits_denominator = form.cleaned_data['credits_denominator']
            equivalent.instructor = instructor
            equivalent.status = 'CONF'
            equivalent.save()
            messages.add_message(request, messages.SUCCESS, "Teaching Equivalent successfully created")
            return HttpResponseRedirect(reverse('planning.views.view_teaching_credits_admin', kwargs={'userid': userid}))
    else:
        form = TeachingEquivForm()
    return render(request, 'planning/new_teaching_equiv_admin.html', {'form': form, 'instructor': instructor})