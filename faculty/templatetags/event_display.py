from django import template
register = template.Library()

@register.filter
def get_config(event, field):
    val = event.config.get(field, 'unknown')
    return val
