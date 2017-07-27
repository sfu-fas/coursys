from django import template
register = template.Library()


# Get an event's content based on its handler
@register.filter
def get_event_value(handler, field):
    return handler.get_config(field)


# Same thing, but get the value directly from the event, not its handler
@register.filter
def get_event_value_direct(event, field):
    return event.config.get(field, None)
