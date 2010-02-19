from django.contrib.auth.decorators import login_required
from coredata.models import Member, CourseOffering
from django.shortcuts import render_to_response, get_object_or_404#, redirect
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from courselib.auth import requires_course_by_slug
from submission.forms import *
from dashboard.templatetags.course_display import display_form
from courselib.auth import is_course_staff_by_slug, is_course_member_by_slug, requires_course_staff_by_slug
from submission.models import select_all_components

@login_required
def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    return render_to_response("submission/index.html", {'memberships': memberships}, context_instance=RequestContext(request))


@login_required
def show_components(request, course_slug, activity_slug):
    #if course staff
    if is_course_staff_by_slug(request.user, course_slug):
	return _show_components_staff(request, course_slug, activity_slug)
    #else course member
    elif is_course_member_by_slug(request.user, course_slug):
	return _show_components_student(request, course_slug, activity_slug)
    #else not found, return 403
    else:
	resp = render_to_response('403.html', context_instance=RequestContext(request))
        resp.status_code = 403
        return resp

@login_required
def _show_components_student(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    # TODO: finish student's view
    return render_to_response("submission/component_view.html",
	{"course":course, "activity":activity},
	context_instance=RequestContext(request))

@login_required
def _show_components_staff(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    component_set = select_all_components(activity)
    component_updated = None
    form_errors = None
    form_set = None
    return render_to_response("submission/component_edit.html",
        {"course":course, "activity":activity, "form_set":form_set, "updated":component_updated, "errors":form_errors},
        context_instance=RequestContext(request))
    
@requires_course_staff_by_slug
def add_component(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    new_component_added = None

    #default, Archive
    type = request.GET.get('type')
    if type == None:
	type = 'Archive'

    if type == 'Archive':
	form = ArchiveComponentForm()
	new_form = ArchiveComponentForm(request.POST)
    elif type == 'URL':
	form = URLComponentForm()
	new_form = URLComponentForm(request.POST)
    elif type == 'Cpp':
	form = CppComponentForm()
	new_form = CppComponentForm(request.POST)
    elif type == 'PlainText':
	form = PlainTextComponentForm()
	new_form = PlainTextComponentForm(request.POST)
    elif type == 'Java':
	form = JavaComponentForm()
	new_form = JavaComponentForm(request.POST)
    else:
	raise Http404()

    #if form is submitted, validate / update component
    if request.method == 'POST':
	#incoming_form = AddComponentForm(request.POST)
        if new_form.is_valid():
            #add component
            new_component = new_form.save(commit=False)
            new_component.activity = activity
            if new_component.position == None:
                count = len(select_all_components(activity))
                new_component.position = count + 1
            new_component.save()
            new_component_added = True
	else:
	    form = new_form

    return render_to_response("submission/component_add.html",
	{"course":course, "activity":activity, "form":form, "new_added":new_component_added, "type":type},
	context_instance=RequestContext(request))