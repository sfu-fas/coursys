from django.shortcuts import render, get_object_or_404
from courselib.auth import requires_role

from .models import Contact, Event


@requires_role('RELA')
def index(request):
    contacts = Contact.objects.filter(unit__in=request.units)


@requires_role('RELA')
def view_contact(request, contact_slug):
    contact = get_object_or_404(Contact, slug=contact_slug, unit__in=request.units)
    events = Event.objects.filter(contact=contact)
