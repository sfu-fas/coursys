from django import template
from django.utils.safestring import mark_safe

register = template.Library()


#@register.filter()
#def get_component_type(component):
#    str = component.get_type()
#    return mark_safe(str)
