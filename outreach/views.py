from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from .models import OutreachEvent, OutreachEventRegistration
from .forms import OutreachEventForm, OutreachEventRegistrationForm
from courselib.auth import requires_role
from log.models import LogEntry
from coredata.models import Unit, Role
from courselib.auth import ForbiddenResponse
import unicodecsv as csv
from datetime import datetime



def _has_unit_role(user, event):
    """
    A quick method to check that the person has the Outreach Admin role for the given event's unit.
    """
    return Role.objects.filter(person__userid=user.username, role='OUTR', unit=event.unit).count() > 0

@requires_role('OUTR')
def outreach_index(request):
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
            return HttpResponseRedirect(reverse('outreach_index'))
    else:
        form = OutreachEventForm(request)
    return render(request, 'outreach/new_event.html', {'form': form})


@requires_role('OUTR')
def view_event(request, event_slug):
    event = get_object_or_404(OutreachEvent, slug=event_slug)
    if not _has_unit_role(request.user, event):
        return ForbiddenResponse(request)
    register_url = request.build_absolute_uri(reverse('register', kwargs={'event_slug': event.slug}))
    return render(request, 'outreach/view_event.html', {'event': event, 'register_url': register_url})


@requires_role('OUTR')
def edit_event(request, event_slug):
    event = get_object_or_404(OutreachEvent, slug=event_slug)
    if not _has_unit_role(request.user, event):
        return ForbiddenResponse(request)
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
            return HttpResponseRedirect(reverse('outreach_index'))
    else:
        form = OutreachEventForm(request, instance=event)
    return render(request, 'outreach/edit_event.html', {'form': form, 'event_slug': event.slug})


@requires_role('OUTR')
def delete_event(request, event_id):
    event = get_object_or_404(OutreachEvent, pk=event_id)
    if not _has_unit_role(request.user, event):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Hid event %s' % event)
        l = LogEntry(userid=request.user.username,
                     description="Deleted event: %s" % event,
                     related_object=event)
        l.save()
    return HttpResponseRedirect(reverse('outreach_index'))


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
            l = LogEntry(userid='',
                         description="Registered %s for event %s" % (registration.fullname(), registration.event.title),
                         related_object=registration
                         )
            l.save()
            return HttpResponseRedirect(reverse('register_success', kwargs={'event_slug': event_slug}))
    else:
        form = OutreachEventRegistrationForm()
    return render(request, 'outreach/register.html', {'form': form, 'event': event})


def register_success(request, event_slug):
    """
    CAREFUL, this view is open to the whole world.
    """
    event = get_object_or_404(OutreachEvent, slug=event_slug)
    return render(request, 'outreach/registered.html', {'event': event})


@requires_role('OUTR')
def view_all_registrations(request):
    unit_ids = [unit.id for unit in request.units]
    units = Unit.objects.filter(id__in=unit_ids)
    current_registrations = OutreachEventRegistration.objects.current(units).order_by('event__start_date')
    past_registrations = OutreachEventRegistration.objects.past(units).order_by('event__start_date')
    context = {'current_registrations': current_registrations, 'past_registrations': past_registrations}
    return render(request, 'outreach/all_registrations.html', context)


@requires_role('OUTR')
def view_registration(request, registration_id):
    registration = get_object_or_404(OutreachEventRegistration, pk=registration_id)
    if not _has_unit_role(request.user, registration.event):
        return ForbiddenResponse(request)
    return render(request, 'outreach/view_registration.html', {'registration': registration})


@requires_role('OUTR')
def edit_registration(request, registration_id, event_slug=None):
    registration = get_object_or_404(OutreachEventRegistration, pk=registration_id)
    if not _has_unit_role(request.user, registration.event):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        form = OutreachEventRegistrationForm(request.POST, instance=registration)
        if form.is_valid():
            registration = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Registration was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited registration for %s" % registration,
                         related_object=registration)
            l.save()
            if event_slug:
                return HttpResponseRedirect(reverse(view_event_registrations, kwargs={'event_slug': event_slug}))
            return HttpResponseRedirect(reverse(view_all_registrations))
    else:
        form = OutreachEventRegistrationForm(instance=registration, initial={'confirm_email': registration.email})
    return render(request, 'outreach/edit_registration.html', {'form': form, 'registration': registration,
                                                               'event_slug': event_slug})


@requires_role('OUTR')
def delete_registration(request, registration_id, event_slug=None):
    registration = get_object_or_404(OutreachEventRegistration, pk=registration_id)
    if not _has_unit_role(request.user, registration.event):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        registration.delete()
        messages.success(request, 'Hid registration %s' % registration)
        l = LogEntry(userid=request.user.username,
                     description="Deleted registration: %s" % registration,
                     related_object=registration)
        l.save()
    if event_slug:
        return HttpResponseRedirect(reverse(view_event_registrations, kwargs={'event_slug': event_slug}))
    return HttpResponseRedirect(reverse(view_all_registrations))

@requires_role('OUTR')
def toggle_registration_attendance(request, registration_id, event_slug=None):
    registration = get_object_or_404(OutreachEventRegistration, pk=registration_id)
    if not _has_unit_role(request.user, registration.event):
        return ForbiddenResponse(request)
    if request.method == 'POST':
        registration.attended = not registration.attended
        registration.save()
        messages.success(request, 'Toggle attendance for %s' % registration)
        l = LogEntry(userid=request.user.username,
                     description="Toggled attendance for registration: %s" % registration,
                     related_object=registration)
        l.save()
    if event_slug:
        return HttpResponseRedirect(reverse(view_event_registrations, kwargs={'event_slug': event_slug}))
    return HttpResponseRedirect(reverse(view_all_registrations))


@requires_role('OUTR')
def view_event_registrations(request, event_slug):
    event = get_object_or_404(OutreachEvent, slug=event_slug)
    if not _has_unit_role(request.user, event):
        return ForbiddenResponse(request)
    registrations = OutreachEventRegistration.objects.filter(event=event, hidden=False)
    return render(request, 'outreach/event_registrations.html', {'event': event, 'registrations': registrations})


@requires_role('OUTR')
def download_current_events_csv(request, past=None):
    unit_ids = [unit.id for unit in request.units]
    units = Unit.objects.filter(id__in=unit_ids)
    if not past:
        events = OutreachEvent.objects.current(units)
        filestring = "current"
    else:
        events = OutreachEvent.objects.past(units)
        filestring = "past"
    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = 'inline; filename="outreach_events-%s-%s.csv"' % \
                                      (datetime.now().strftime('%Y%m%d'), filestring)
    writer = csv.writer(response)
    if events:
        writer.writerow(['Title', 'Start Date', 'End Date', 'Description', 'Location', 'Unit', 'Resources',
                         'Cost', 'Notes', 'Email', 'Attendance', 'Registration Link'])
        for e in events:
            writer.writerow([e.title, e.start_date, e.end_date, e.description, e.location, e.unit, e.resources, e.cost,
                             e.notes, e.email, e.registration_count(),
                             request.build_absolute_uri(reverse('register', kwargs={'event_slug': e.slug}))])
    return response


@requires_role('OUTR')
def download_registrations(request, event_slug=None, past=None):
    """
    We can reach this view from a few places.  If it's from a specific event, that should override all, and get the
    registrations just for that event.  Otherwise, it's from the page with all registrations, and it should then
    have a flag set for current or past registrations.
    """
    if event_slug:
        event = get_object_or_404(OutreachEvent, slug=event_slug)
        registrations = OutreachEventRegistration.objects.by_event(event)
        filestring = event.slug
        #  If you're just getting one event's worth, you probably don't want the event name in every row.
        header_row_initial = []
    else:
        unit_ids = [unit.id for unit in request.units]
        units = Unit.objects.filter(id__in=unit_ids)
        # But if you're getting all of them, you probably do.
        header_row_initial = ['Event']
        if past:
            registrations = OutreachEventRegistration.objects.past(units)
            filestring = "all_past"
        else:
            registrations = OutreachEventRegistration.objects.current(units)
            filestring = "all_current"

    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = 'inline; filename="outreach_registrations-%s-%s.csv"' % \
                                      (datetime.now().strftime('%Y%m%d'), filestring)
    writer = csv.writer(response)
    if registrations:
        header_row = header_row_initial + ['Last Name', 'First Name', 'Middle Name', 'Age', 'Parent Name',
                                           'Parent Phone', 'Email', 'Waiver', 'Previously Attended', 'School',
                                           'Grade', 'Notes', 'Attended(ing)', 'Registered at', 'Last Modified']
        writer.writerow(header_row)
        for r in registrations:
            # Same rationale as above
            if event_slug:
                initial_regitration_row = []
            else:
                initial_regitration_row = [r.event.title]
            registration_row = initial_regitration_row + [r.last_name, r.first_name, r.middle_name, r.age,
                                                          r.parent_name, r.parent_phone, r.email, r.waiver,
                                                          r.previously_attended, r.school, r.grade, r.notes, r.attended,
                                                          r.created_at, r.last_modified]
            writer.writerow(registration_row)
    return response
