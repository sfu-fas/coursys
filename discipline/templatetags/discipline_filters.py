from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from discipline.models import STEP_DESC

register = template.Library()

@register.filter()
@stringfilter
def format_text(value):
    """
    Format long-form text as required by the discipline module
    """
    return mark_safe("<p>" + escape(value) + "</p>")

@register.filter()
def edit_link(case, field):
    """
    An "edit this thing" link for the corresponding field
    """
    return mark_safe('<p class="editlink"><a href="%s">Edit %s</a></p>' % (reverse('discipline.views.edit_'+field,
            kwargs={'course_slug':case.student.offering.slug, 'case_slug': case.slug}), STEP_DESC[field]))
