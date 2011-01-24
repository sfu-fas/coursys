from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter()
@stringfilter
def format_text(value):
    """
    Format long-form text as required by the discipline module
    """
    return mark_safe("<p>" + escape(value) + "</p>")

