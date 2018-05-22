from django.shortcuts import render, get_object_or_404, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from courselib.auth import get_person
from coredata.models import Role
from .models import Reminder
from .forms import ReminderForm


@login_required
def index(request):
    person = get_person(request.user)
    user_roles = Role.objects_fresh.filter(person=person)
    Reminder.create_all_reminder_messages()
    
    personal_reminders = Reminder.objects.filter(person=person).select_related('course')
    # TODO: find role reminders
    role_reminders = Reminder.objects.none().select_related('unit')
    
    reminders = list(personal_reminders) + list(role_reminders)
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
def view(request, reminder_slug):
    reminder = get_object_or_404(Reminder, slug=reminder_slug)
    person = get_person(request.user)
    if not reminder.can_be_accessed_by(person):
        raise get_object_or_404(Reminder, reminder_type='FOO', person=None) # make error same as above

    context = {
        'reminder': reminder,
    }
    return render(request, 'reminders/view.html', context)
