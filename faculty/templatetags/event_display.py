from django import template
register = template.Library()

@register.filter
def get_config(event, field):
    val = event.config.get(field, 'unknown')
    return val


@register.filter
def can_approve(person, handler):
    if handler.can_approve(person):
        print handler.can_approve(person)
        return True
    return False
