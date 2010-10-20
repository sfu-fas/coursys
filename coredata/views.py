from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from forms import *
from courselib.auth import *
from coredata.models import *
from log.models import LogEntry
from django.core.urlresolvers import reverse

@requires_role("SYSA")
def sysadmin(request):
    return render_to_response('coredata/sysadmin.html', {}, context_instance=RequestContext(request))

@requires_role("SYSA")
def role_list(request):
    """
    Display list of who has what role
    """
    roles = Role.objects.all()
    
    return render_to_response('coredata/roles.html', {'roles': roles}, context_instance=RequestContext(request))

@requires_role("SYSA")
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


@requires_role("SYSA")
def members_list(request):
    members = Member.objects.exclude(added_reason="AUTO")
    return render_to_response('coredata/members_list.html', {'members': members}, context_instance=RequestContext(request))


@requires_role("SYSA")
def edit_member(request, member_id=None):
    if member_id:
        member = get_object_or_404(Member, id=member_id)
    else:
        member = None

    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
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

    return render_to_response('coredata/edit_member.html', {'form': form, 'member': member}, context_instance=RequestContext(request))


@requires_role("SYSA")
def user_summary(request, userid):
    user = get_object_or_404(Person, userid=userid)
    
    memberships = Member.objects.filter(person=user)
    roles = Role.objects.filter(person=user).exclude(role="NONE")
    
    context = {'user': user, 'memberships': memberships, 'roles': roles}
    return render_to_response("coredata/user_summary.html", context ,context_instance=RequestContext(request))


@requires_role("SYSA")
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


