from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import escape
from django.utils.text import wrap
from django.utils.safestring import mark_safe
from django.urls import reverse
from discipline.models import STEP_DESC, STEP_VIEW, PRE_LETTER_STEPS
from textile import textile_restricted

register = template.Library()

@register.filter()
def format_field(case, field):
    """
    Format long-form text as required by the discipline module, making substitutions as appropriate.
    """
    text = eval("case."+field)
    if text is None or text.strip() == "":
        return mark_safe('<p class="empty">None</p>')
    
    if field == 'contact_email_text':
        # special case: contact email is plain text
        return mark_safe("<pre>" + escape(wrap(case.substitite_values(str(text)), 78)) + "</pre>")
    else:
        return mark_safe('<div class="disc-details">' + textile_restricted(case.substitite_values(str(text)), lite=False) + '</div>')

@register.filter()
def edit_link(case, field):
    """
    An "edit this thing" link for the corresponding field
    """
    if case.ro_display:
        return ""
    if not case.can_edit(field):
        return ""
    return mark_safe('<p class="editlink"><a href="%s">Edit %s</a></p>' % (reverse('offering:discipline:edit_case_info',
            kwargs={'course_slug':case.offering.slug, 'case_slug': case.slug, 'field': STEP_VIEW[field]}), STEP_DESC[field]))

@register.filter()
def chair_edit_link(case, field):
    """
    An "edit this thing" link for the corresponding field: chair's display
    """
    if case.chair_done():
        return ""
    return mark_safe('<p class="editlink"><a href="%s">Edit %s</a></p>' % (reverse('offering:discipline:edit_case_info',
            kwargs={'course_slug':case.offering.slug, 'case_slug': case.slug, 'field': STEP_VIEW[field]}), STEP_DESC[field]))
