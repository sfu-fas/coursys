from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape
register = template.Library()

@register.filter
def panel_info(data):
    if not data:
        return mark_safe('<p class="empty">None</p>')
    out = []
    out.append('<dl class="panel-info">')
    for k,v in data:
        out.append('<dt>')
        out.append(escape(k))
        out.append('</dt><dd>')
        out.append(escape(v))
        out.append('</dd>')
    out.append('</dl>')
    return mark_safe(''.join(out))