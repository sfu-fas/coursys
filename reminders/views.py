from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Q

from courselib.auth import get_person, HttpError
from coredata.models import Role
from log.models import LogEntry
from .models import Reminder, ReminderMessage, MESSAGE_EARLY_CREATION, HISTORY_RETENTION
from .forms import ReminderForm

import operator
from functools import reduce


@login_required
def index(request):
    person = get_person(request.user)

    # PERS, INST reminders for this person
    personal_reminders = Reminder.objects.filter(reminder_type__in=['PERS','INST'], person=person).select_related('course')

    # ROLE reminders for this person's current roles
    user_roles = Role.objects_fresh.filter(person=person)
    role_query = reduce(
        operator.or_,
        (Q(role=r.role) & Q(unit=r.unit) for r in user_roles)
        )
    role_reminders = Reminder.objects.filter(role_query, reminder_type='ROLE').select_related('unit')

    reminders = set(personal_reminders) | set(role_reminders)
    context = {
        'reminders': reminders,
    }
    return render(request, 'reminders/index.html', context)


@login_required
def create(request):
    person = get_person(request.user)
    if request.method == 'POST':
        form = ReminderForm(data=request.POST, person=person)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.person = person
            reminder.save()
            l = LogEntry(userid=request.user.username,
                         description="created reminder %s" % (reminder.slug,),
                         related_object=reminder
                         )
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Reminder created.')
            return HttpResponseRedirect(reverse('reminders:view', kwargs={'reminder_slug': reminder.slug}))

    else:
        form = ReminderForm(person=person)

    context = {
        'form': form,
    }
    return render(request, 'reminders/create.html', context)


def _get_reminder_or_404(request, reminder_slug):
    """
    Get the reminder *if* the logged-in user is allowed to view/edit it. Else raise 404.
    """
    reminder = get_object_or_404(Reminder, slug=reminder_slug)
    person = get_person(request.user)
    if not reminder.can_be_accessed_by(person):
        get_object_or_404(Reminder, reminder_type='FOO', person=None) # make error same as above
        raise ValueError() # shouldn't happen, but definitely don't continue error-free from here.
    return reminder, person


@login_required
def view(request, reminder_slug):
    reminder, _ = _get_reminder_or_404(request, reminder_slug)
    messages = ReminderMessage.objects.filter(reminder=reminder).select_related('person')
    future_messages = messages.filter(sent=False).order_by('date', 'person')
    sent_messages = messages.filter(sent=True).order_by('sent_at', 'person')

    context = {
        'reminder': reminder,
        'future_messages': future_messages,
        'sent_messages': sent_messages,
        'future_days': MESSAGE_EARLY_CREATION,
        'sent_days': HISTORY_RETENTION,
    }
    return render(request, 'reminders/view.html', context)


@login_required
def edit(request, reminder_slug):
    reminder, person = _get_reminder_or_404(request, reminder_slug)
    if request.method == 'POST':
        form = ReminderForm(instance=reminder, data=request.POST, person=person)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.person = person
            reminder.save()
            l = LogEntry(userid=request.user.username,
                         description="edited reminder %s" % (reminder.slug,),
                         related_object=reminder
                         )
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Reminder updated.')
            return HttpResponseRedirect(reverse('reminders:view', kwargs={'reminder_slug': reminder.slug}))

    else:
        form = ReminderForm(instance=reminder, person=person)

    context = {
        'form': form,
        'reminder': reminder,
    }
    return render(request, 'reminders/edit.html', context)


@login_required
def delete(request, reminder_slug):
    if request.method != 'POST':
        return HttpError(request, status=405, title="Method not allowed", error="This URL accepts only POST requests", errormsg=None)

    reminder, person = _get_reminder_or_404(request, reminder_slug)
    reminder.person = person
    reminder.status = 'D'
    reminder.save()
    l = LogEntry(userid=request.user.username,
                 description="deleted reminder %s" % (reminder.slug,),
                 related_object=reminder
                 )
    l.save()

    messages.add_message(request, messages.SUCCESS, 'Reminder deleted.')
    return HttpResponseRedirect(reverse('reminders:index', kwargs={}))
