from planning.forms import CourseForm
from courselib.auth import requires_role
from log.models import LogEntry
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext


@requires_role('PLAN')
def create_course(request):
    units = [(u.id, str(u)) for u in request.units]
    if request.method == 'POST':
        form = CourseForm(request.POST)
        form.fields['owner'].choices = units
        if form.is_valid():
            course = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("added course %s %s") % (course.subject, course.number),
                  related_object=course)
            l.save()

            messages.add_message(request, messages.SUCCESS, 'Added course %s.' % (course))

            return HttpResponseRedirect(reverse('planning.views.manage_courses', kwargs={}))
    else:
        form = CourseForm()
        form.fields['owner'].choices = units

    return render(request, "planning/create_course.html", {'form': form})
