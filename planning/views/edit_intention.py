from planning.models import TeachingIntention
from planning.forms import IntentionForm
from courselib.auth import requires_instructor
from coredata.models import Person, Semester
from log.models import LogEntry
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext
from datetime import datetime


@requires_instructor
def edit_intention(request):
    instructor = get_object_or_404(Person, userid=request.user.username)
    semester_list = Semester.objects.filter(start__gt=datetime.now())
    intention_list = TeachingIntention.objects.filter(instructor=instructor).order_by('semester')

    if request.method == 'POST':
        form = IntentionForm(request.POST)
        form.instructor_id = instructor.id
        if form.is_valid():
            intention = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("added teaching intention for %s") % (intention.semester),
                      related_object=intention)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Added semester plan for %s.' % (intention.semester))
            return HttpResponseRedirect(reverse('planning.views.edit_intention', kwargs={}))
    else:
        form = IntentionForm(initial={'instructor': instructor})
        form.fields['semester'].choices = [(s.pk, s) for s in semester_list]

    return render_to_response("planning/add_intention.html", {'form': form, 'intention_list': intention_list}, context_instance=RequestContext(request))
