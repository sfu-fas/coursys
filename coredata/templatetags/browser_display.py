from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape
register = template.Library()

TEMPLATE = """<li><label for="{id}">{label}</label><span class="field">{field}</span></li>"""

@register.filter
def browser_field(field):
    context = {
        'id': field.id_for_label,
        'label': escape(field.label),
        'field': str(field),
        }
    return mark_safe(TEMPLATE.format(**context))

