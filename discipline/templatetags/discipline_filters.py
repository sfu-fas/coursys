from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import escape
from django.utils.text import wrap
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from discipline.models import STEP_DESC, STEP_VIEW
import external.textile as textile
Textile = textile.Textile(restricted=True)

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
        return mark_safe("<pre>" + escape(wrap(case.substitite_values(unicode(text)), 78)) + "</pre>")
    else:
        return mark_safe(Textile.textile(case.substitite_values(unicode(text))))

@register.filter()
def edit_link(case, field):
    """
    An "edit this thing" link for the corresponding field
    """
    if case.instr_done():
        return ""
    return mark_safe('<p class="editlink"><a href="%s">Edit %s</a></p>' % (reverse('discipline.views.edit_case_info',
            kwargs={'course_slug':case.offering.slug, 'case_slug': case.slug, 'field': STEP_VIEW[field]}), STEP_DESC[field]))
