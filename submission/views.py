from django.contrib.auth.decorators import login_required
from coredata.models import Member, CourseOffering
from django.shortcuts import render_to_response, get_object_or_404#, redirect
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from courselib.auth import requires_course_by_slug
from submission.forms import AddComponentForm
from dashboard.templatetags.course_display import display_form
from courselib.auth import is_course_staff_by_slug, is_course_member_by_slug

@login_required
def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    return render_to_response("submission/index.html", {'memberships': memberships}, context_instance=RequestContext(request))


@login_required
def show_components(request, course_slug, activity_shortname):
    #if course staff
    if is_course_staff_by_slug(request.user, course_slug):
	return _show_components_instructor(request, course_slug, activity_shortname)
    #else course member
    elif is_course_member_by_slug(request.user, course_slug):
	return _show_components_student(request, course_slug, activity_shortname)
    #else not found
    else:
	raise Http404()

@login_required
def _show_components_student(request, course_slug, activity_shortname):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,short_name = activity_shortname)
    return render_to_response("submission/component_view.html",
	{},
	context_instance=RequestContext(request))

@login_required
def _show_components_instructor(request, course_slug, activity_shortname):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, short_name = activity_shortname)
    form = AddComponentForm()
    new_component_added = None

    #if user is staff member, update/add component
    if request.method == 'POST':
	incoming_form = AddComponentForm(request.POST)
        if incoming_form.is_valid():
	    #TODO: update/add component
            new_component_added = True
	else:
	    form = incoming_form

    #get all components
    #TODO: components =

    return render_to_response("submission/component_edit.html",
        {"activity":activity, "form":form, "new_added":new_component_added},
        context_instance=RequestContext(request))
    
