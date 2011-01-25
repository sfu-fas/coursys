from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from discipline.models import STEP_DESC, STEP_VIEW
import external.textile as textile
Textile = textile.Textile(restricted=True)

register = template.Library()

@register.filter()
def format_text(value):
    """
    Format long-form text as required by the discipline module
    """
    if value is None:
        return mark_safe('<p class="empty">None</p>')
    
    return mark_safe(Textile.textile(unicode(value)))

@register.filter()
def edit_link(case, field):
    """
    An "edit this thing" link for the corresponding field
    """
    return mark_safe('<p class="editlink"><a href="%s">Edit %s</a></p>' % (reverse('discipline.views.edit_'+STEP_VIEW[field],
            kwargs={'course_slug':case.student.offering.slug, 'case_slug': case.slug}), STEP_DESC[field]))
