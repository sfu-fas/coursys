from courselib.markup import markup_to_html
from dashboard.templatetags.form_display import field_display, label_display
from django import template
from django.forms import Field
from django.utils.html import escape
from django.utils.text import wrap
from django.utils.safestring import mark_safe, SafeString
from django.urls import reverse
from discipline.models import DisciplineCaseBase

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
        text = case.substitite_values(str(text))
        markup = case.config.get(field+'_markup', 'textile')
        html = markup_to_html(text, markuplang=markup, math=False, restricted=True)
        return mark_safe('<div class="disc-details">' + html + '</div>')


@register.simple_tag(takes_context=True)
def discipline_action(context: dict, case: DisciplineCaseBase, field: str, value: str, text: SafeString) -> SafeString:
    csrf_token = context.get('csrf_token')
    url = reverse('offering:discipline:'+field, kwargs={'course_slug': case.offering.slug, 'case_slug': case.slug})
    if value:
        markup = f'''<li><form action="{url}" method="post" enctype="multipart/form-data">
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}" />
            <button type="submit" name="{escape(field)}" value="{escape(value)}">{text}</button>
            </form></li>'''
    else:
        markup = f'''<li><a href="{url}">{text}</a></li>'''
    return mark_safe(markup)


done_markup = mark_safe('<i class="fa fa-check successmessage" title="This step seems complete."></i>')
not_done_markup = mark_safe('<i class="fa fa-question infomessage" title="Incomplete: see below."></i>')


@register.simple_tag()
def step_done_unless(case, value, target) -> SafeString:
    return done_markup if (value != target or case.penalty == 'NONE') else not_done_markup


@register.simple_tag()
def step_done_if_truthy(case, value) -> SafeString:
    return done_markup if (value or case.penalty == 'NONE') else not_done_markup


@register.simple_tag()
def step_done_send(case) -> SafeString:
    return done_markup if (case.letter_sent != 'WAIT' or case.penalty == 'NONE') else not_done_markup


@register.filter()
def discipline_field(field: Field) -> SafeString:
    if field.field.templates:
        template_html = f'<div class="discside" id="templates_{field.name}"><h3>Templates</h3><ul>'
        for t in field.field.templates:
            template_html += f'<li><a class="template-link" data-field="id_{field.name}" data-text="{escape(t.text)}">{escape(t.label)}</a></li>'
        template_html += '</ul></div>'
    else:
        template_html = ''
    return mark_safe(f'<dt>{label_display(field)}</dt><dd>{template_html}{field_display(field)}</dd>')