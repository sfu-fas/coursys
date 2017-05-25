from django.shortcuts import render, get_object_or_404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib import messages
from courselib.auth import requires_role
from forms import ContactForm
from log.models import LogEntry

from .models import Contact, Event


@requires_role('RELA')
def index(request):
    contacts = Contact.objects.filter(unit__in=request.units)
    return render(request, 'relationships/index.html', {'contacts': contacts})


@requires_role('RELA')
def view_contact(request, contact_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    events = Event.objects.filter(contact=contact)
    return render(request, 'relationships/view_contact.html', {'contact': contact, 'events': events})


@requires_role('RELA')
def new_contact(request):
    if request.method == 'POST':
        print "in POST"
        form = ContactForm(request, request.POST)
        if form.is_valid():
            contact = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Contact was created')
            l = LogEntry(userid=request.user.username,
                         description="Added contact %s" % contact,
                         related_object=contact)
            l.save()
            return HttpResponseRedirect(reverse('relationships:index'))
    else:
        print "In GET"
        form = ContactForm(request)
    return render(request, 'relationships/new_contact.html', {'form': form})


@requires_role('RELA')
def edit_contact(request, contact_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    if request.method == 'POST':
        form = ContactForm(request, request.POST, instance=contact)
        if form.is_valid():
            contact = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Contact was edited')
            l = LogEntry(userid=request.user.username,
                         description="Edited contact %s" % contact,
                         related_object=contact)
            l.save()
            return HttpResponseRedirect(reverse('relationships:index'))
    else:
        form = ContactForm(request, instance=contact)
    return render(request, 'relationships/edit_contact.html', {'form': form, 'contact': contact})


@requires_role('RELA')
def delete_contact(request, contact_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    if request.method == 'POST':
        contact.deleted = True
        contact.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             u'Contact was deleted')
        l = LogEntry(userid=request.user.username,
                     description="Deleted contact %s" % contact,
                     related_object=contact)
        l.save()
    return HttpResponseRedirect(reverse('relationships:index'))
