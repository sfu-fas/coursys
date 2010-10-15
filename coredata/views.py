from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from forms import *
from courselib.auth import *
from coredata.models import *
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
            return HttpResponseRedirect(reverse(members_list))
    elif member_id:
        form = MemberForm(instance=member, initial={'person': member.person.userid})
    else:
        form = MemberForm()

    return render_to_response('coredata/edit_member.html', {'form': form, 'member': member}, context_instance=RequestContext(request))


