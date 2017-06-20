from django import template
register = template.Library()


@register.filter
def get_event_value(handler, field):
    return handler.get_config(field)
