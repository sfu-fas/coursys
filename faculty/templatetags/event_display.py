from django import template
register = template.Library()

from faculty.event_types.base import CareerEventHandlerBase


@register.filter
def get_config(event, field):
    if isinstance(event, CareerEventHandlerBase):
        return event.get_config(field, 'unknown')
    else:
        return event.config.get(field, 'unknown')


@register.filter
def can_approve(person, handler):
    if handler.can_approve(person):
        return True
    return False
