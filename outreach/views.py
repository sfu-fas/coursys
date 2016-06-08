from django.shortcuts import render, HttpResponseRedirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
from .models import OutreachEvent, OutreachEventRegistration
from .forms import OutreachEventForm, OutreachEventRegistrationForm
from courselib.auth import requires_role
from log.models import LogEntry
from coredata.models import Unit


@requires_role('OUTR')
def index(request):
    unit_ids = [unit.id for unit in request.units]
    units = Unit.objects.filter(id__in=unit_ids)
    events = OutreachEvent.objects.current(units)
    past_events = OutreachEvent.objects.past(units)
    return render(request, 'outreach/index.html', {'events': events, 'past_events': past_events})


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
def view_event(request, event_slug):
    event = get_object_or_404(OutreachEvent, slug=event_slug)
    register_url = request.build_absolute_uri(reverse('register', kwargs={'event_slug': event.slug}))
    return render(request, 'outreach/view_event.html', {'event': event, 'register_url': register_url})


@requires_role('OUTR')
def edit_event(request, event_slug):
    event = get_object_or_404(OutreachEvent, slug=event_slug)
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
    return render(request, 'outreach/edit_event.html', {'form': form, 'event_slug': event.slug})


@requires_role('OUTR')
def delete_event(request, event_id):
    event = get_object_or_404(OutreachEvent, pk=event_id)
    if request.method == 'POST':
        messages.success(request, 'Hid event %s' % event)
        l = LogEntry(userid=request.user.username,
                     description="Deleted event: %s" % event,
                     related_object=event)
        l.save()

        event.delete()
    return HttpResponseRedirect(reverse(index))


def register(request, event_slug):
    """
    CAREFUL, this view is open to the whole world.
    """
    event = get_object_or_404(OutreachEvent, slug=event_slug)
    if request.method == 'POST':
        form = OutreachEventRegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.event = event
            registration.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Successfully registered')
            l = LogEntry(userid=registration.name,
                         description="Registered %s for event %s" % (registration, registration.event),
                         related_object=registration)
            l.save()
            return HttpResponseRedirect(reverse('index'))
    else:
        form = OutreachEventRegistrationForm()
    return render(request, 'outreach/register.html', {'form': form, 'event': event})




