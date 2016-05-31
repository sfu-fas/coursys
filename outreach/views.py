from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from .models import OutreachEvent, OutreachEventRegistration
from .forms import OutreachEventForm, OutreachEventRegistrationForm
from courselib.auth import requires_role
from log.models import LogEntry
from datetime import datetime
from coredata.models import Unit


@requires_role('OUTR')
def index(request):
    unit_ids = [unit.id for unit in request.units]
    units = Unit.objects.filter(id__in=unit_ids)
    events = OutreachEvent.objects.visible(units)
    return render(request, 'outreach/index.html', {'events': events})


@requires_role('OUTR')
def new_event(request):
    if request.method == 'POST':
        form = OutreachEventForm(request, request.POST)
        if form.is_valid():
            event = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Event was created')
            l = LogEntry(userid=request.user.username,
                         description="Added event %s" % event,
                         related_object=event)
            l.save()
            return HttpResponseRedirect(reverse('index'))
    else:
        form = OutreachEventForm(request)
    return render(request, 'outreach/new_event.html', {'form': form})


@requires_role('OUTR')
def view_event(request, event_id):
    #TODO a simple template to view event
    pass


@requires_role('OUTR')
def edit_event(request, event_id):
    event = get_object_or_404(OutreachEvent, pk=event_id)
    if request.method == 'POST':
        form = OutreachEventForm(request, request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Event was saved')
            l = LogEntry(userid=request.user.username,
                         description="Edited event %s" % event,
                         related_object=event)
            l.save()
            return HttpResponseRedirect(reverse('index'))
    else:
        form = OutreachEventForm(request, instance=event)
    return render(request, 'outreach/edit_event.html', {'form': form, 'event_id': event_id})



@requires_role('OUTR')
def delete_event(request, event_id):
    event = get_object_or_404(OutreachEvent, pk=event_id)
    if request.method == 'POST':
        messages.success(request, 'Hid event %s' % event)
        l = LogEntry(userid=request.user.username,
                     description="Deleted event: %s" % event,
                     related_object=event
                     )
        l.save()

        event.delete()
    return HttpResponseRedirect(reverse(index))




