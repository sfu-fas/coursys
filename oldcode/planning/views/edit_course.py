from planning.models import PlanningCourse
from planning.forms import CourseForm
from courselib.auth import requires_role
from log.models import LogEntry
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext


@requires_role('PLAN')
def edit_course(request, course_slug):
    course = get_object_or_404(PlanningCourse, slug=course_slug)

    units = [(u.id, str(u)) for u in request.units]
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        form.fields['owner'].choices = units

        if form.is_valid():
            course = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited course %s %s") % (course.subject, course.number),
                  related_object=course)
            l.save()

            messages.add_message(request, messages.SUCCESS, 'Edited course %s.' % (course))

            return HttpResponseRedirect(reverse('planning.views.manage_courses', kwargs={}))
    else:
        form = CourseForm(instance=course)
        form.fields['owner'].choices = units

    return render(request, "planning/edit_course.html", {'form': form, 'course': course})
