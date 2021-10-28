from django import template
from django.utils.html import mark_safe
register = template.Library()

@register.filter
def subtract_and_highlight(a, b):
    diff = a-b
    if diff < -0.01:
        return mark_safe('<div style="background-color:#C2B217">%.2f</div>' % (diff))
    return mark_safe("<div>%.2f</div>" % (diff))
