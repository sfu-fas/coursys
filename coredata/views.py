from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from forms import *
from courselib.auth import *
from coredata.models import *
from log.models import LogEntry
from django.core.urlresolvers import reverse
from django.contrib import messages

@requires_global_role("SYSA")
def sysadmin(request):
    if 'q' in request.GET:
        userid = request.GET['q']
        return HttpResponseRedirect(reverse(user_summary, kwargs={'userid': userid}))
        
    return render_to_response('coredata/sysadmin.html', {}, context_instance=RequestContext(request))

@requires_global_role("SYSA")
def role_list(request):
    """
    Display list of who has what role
    """
    roles = Role.objects.exclude(role="NONE")
    
    return render_to_response('coredata/roles.html', {'roles': roles}, context_instance=RequestContext(request))

@requires_global_role("SYSA")
def new_role(request, role=None):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new role: %s as %s") % (form.instance.person.userid, form.instance.role),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse(role_list))
    else:
        form = RoleForm()

    return render_to_response('coredata/new_role.html', {'form': form}, context_instance=RequestContext(request))

@requires_global_role("SYSA")
def delete_role(request, role_id):
    role = get_object_or_404(Role, pk=role_id)
    messages.success(request, 'Deleted role %s for %s.' % (role.get_role_display(), role.person.name()))
    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
          description=("deleted role: %s for %s") % (role.get_role_display(), role.person.name()),
          related_object=role.person)
    l.save()
    
    role.delete()
    return HttpResponseRedirect(reverse(role_list))

@requires_global_role("SYSA")
def missing_instructors(request):
    # build a set of all instructors that don't have an instructor-appropriate role
    roles = dict(((r.person, r.role) for r in Role.objects.filter(role__in=["FAC","SESS","COOP"]).select_related('person')))
    missing = set()
    for o in CourseOffering.objects.filter(graded=True):
        for i in o.member_set.filter(role="INST"):
            if i.person not in roles:
                missing.add(i.person)
    missing = list(missing)
    missing.sort()
    initial = [{'person': p, 'role': None} for p in missing]

    if request.method == 'POST':
        formset = InstrRoleFormSet(request.POST, initial=initial)
        if formset.is_valid():
            count = 0
            for f in formset.forms:
                p = f.cleaned_data['person']
                r = f.cleaned_data['role']
                d = f.cleaned_data['department']
                if r == "NONE" or p not in missing:
                    continue
                
                r = Role(person=p, role=r, department=d)
                r.save()
                count += 1

                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("new role: %s as %s") % (p.userid, r),
                      related_object=r)
                l.save()
            messages.success(request, 'Set instructor roles for %i people.' % (count))
            return HttpResponseRedirect(reverse(role_list))
    else:
        formset = InstrRoleFormSet(initial=initial)

    return render_to_response('coredata/missing_instructors.html', {'formset': formset}, context_instance=RequestContext(request))


@requires_global_role("SYSA")
def members_list(request):
    members = Member.objects.exclude(added_reason="AUTO")
    return render_to_response('coredata/members_list.html', {'members': members}, context_instance=RequestContext(request))


@requires_global_role("SYSA")
def edit_member(request, member_id=None):
    offering_choices = [(c.id, unicode(c)) for c in CourseOffering.objects.filter(graded=True).exclude(component="CAN")]

    if member_id:
        member = get_object_or_404(Member, id=member_id)
    else:
        member = None

    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        form.fields['offering'].choices = offering_choices
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited membership: %s as %s in %s") % (form.instance.person.userid, form.instance.role, form.instance.offering),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse(members_list))
    elif member_id:
        form = MemberForm(instance=member, initial={'person': member.person.userid})
    else:
        form = MemberForm()
    
    form.fields['offering'].choices = offering_choices
    return render_to_response('coredata/edit_member.html', {'form': form, 'member': member}, context_instance=RequestContext(request))


@requires_global_role("SYSA")
def user_summary(request, userid):
    user = get_object_or_404(Person, userid=userid)
    
    memberships = Member.objects.filter(person=user)
    roles = Role.objects.filter(person=user).exclude(role="NONE")
    
    context = {'user': user, 'memberships': memberships, 'roles': roles}
    return render_to_response("coredata/user_summary.html", context ,context_instance=RequestContext(request))


@requires_global_role("SYSA")
def new_person(request):
    if request.method == 'POST':
        form = PersonForm(request.POST)
        if form.is_valid():
            form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new person added: %s (%s)") % (form.instance.name(), form.instance.userid),
                  related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse(sysadmin))
    else:
        form = PersonForm()

    return render_to_response('coredata/new_person.html', {'form': form}, context_instance=RequestContext(request))


