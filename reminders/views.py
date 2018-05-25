from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Q

from courselib.auth import get_person
from coredata.models import Role
from .models import Reminder, ReminderMessage
from .forms import ReminderForm

import operator
from functools import reduce

@login_required
def index(request):
    person = get_person(request.user)

    # TODO: these should be in tasks, not here.
    Reminder.create_all_reminder_messages()
    ReminderMessage.objects.all().update(sent=False)
    ReminderMessage.send_all()
    ReminderMessage.cleanup()

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
            messages.add_message(request, messages.SUCCESS, 'Reminder created')
            return HttpResponseRedirect(reverse('reminders:view', kwargs={'reminder_slug': reminder.slug}))

    else:
        form = ReminderForm(person=person)

    context = {
        'form': form,
    }
    return render(request, 'reminders/create.html', context)


@login_required
def edit(request, reminder_slug):
    # TODO
    raise NotImplementedError()


@login_required
def delete(request, reminder_slug):
    # TODO
    raise NotImplementedError()


@login_required
def view(request, reminder_slug):
    reminder = get_object_or_404(Reminder, slug=reminder_slug)
    person = get_person(request.user)
    if not reminder.can_be_accessed_by(person):
        raise get_object_or_404(Reminder, reminder_type='FOO', person=None) # make error same as above

    context = {
        'reminder': reminder,
    }
    return render(request, 'reminders/view.html', context)
