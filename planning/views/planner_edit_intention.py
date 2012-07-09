from planning.models import Semester, TeachingIntention
from planning.forms import IntentionForm
from courselib.auth import requires_role
from coredata.models import Person
from log.models import LogEntry
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext


@requires_role('PLAN')
def planner_edit_intention(request, semester, userid):
    instructor = get_object_or_404(Person, userid=userid)
    semester = get_object_or_404(Semester, name=semester)
    intention = get_object_or_404(TeachingIntention, semester=semester, instructor__userid=userid)

    if request.method == 'POST':
        form = IntentionForm(request.POST, instance=intention)
        form.instructor_id = instructor.id
        if form.is_valid():
            intention = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("edited teaching intention for %s") % (intention.instructor),
                      related_object=intention)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Edited semester teaching intention for %s.' % (intention.instructor))

            return HttpResponseRedirect(reverse('planning.views.view_semester_intentions', kwargs={'semester': semester.name}))
    else:
        form = IntentionForm(initial={'instructor': instructor}, instance=intention)

    return render_to_response("planning/planner_edit_intention.html", {'semester': semester, 'instructor': instructor, 'form': form}, context_instance=RequestContext(request))
