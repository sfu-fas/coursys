from django import template
register = template.Library()

from faculty.event_types.base import CareerEventHandlerBase
from faculty.models import EVENT_TYPES


@register.filter
def get_config(event, field):
    if isinstance(event, CareerEventHandlerBase):
        return event.get_config(field, 'unknown')
    else:
        return event.config.get(field, 'unknown')


@register.filter
def can_approve(person, event):
    if event.get_handler().can_approve(person):
        return True
    return False


@register.filter
def can_edit(person, event):
    if event.get_handler().can_edit(person):
        return True
    return False


@register.filter
def can_view_handler(person, key):
    Handler = EVENT_TYPES.get(key.upper())
    tmp = Handler.create_for(person)
    if tmp.can_view(person):
        return True
    return False


@register.filter
def can_edit_handler(person, key):
    Handler = EVENT_TYPES.get(key.upper())
    tmp = Handler.create_for(person)
    if tmp.can_edit(person):
        return True
    return False
