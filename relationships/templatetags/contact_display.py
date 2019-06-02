from django import template
register = template.Library()


# Get an event's content based on its handler
@register.filter
def get_event_value(handler, field):
    return handler.get_config(field)


# Same thing, but get the value directly from the event, not its handler
@register.filter
def get_event_value_direct(event, field):
    from relationships.handlers import FileEventBase
    if isinstance(event.get_handler(), FileEventBase):
        return "This is a file.  Please click the view button."
    return event.config.get(field, None)
