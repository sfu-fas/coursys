from planning.models import PlanningCourse
from courselib.auth import requires_role
from log.models import LogEntry
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse


@requires_role('PLAN')
def delete_course(request, course_id):
    course = PlanningCourse.objects.get(pk=course_id)
    course.status = 'HIDE'
    course.save()

    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
          description=("hid course %s %s") % (course.subject, course.number),
          related_object=course)
    l.save()

    messages.add_message(request, messages.SUCCESS, 'Removed course %s.' % (course))

    return HttpResponseRedirect(reverse('planning.views.manage_courses', kwargs={}))
