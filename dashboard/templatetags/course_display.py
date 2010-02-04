from django import template
register = template.Library()

from settings import MEDIA_URL
from django.template import Context, Template
from django.utils.safestring import mark_safe


FIELD_TEMPLATE = Template('''<li>
                    {{ field.label_tag }}
                    <div class="inputfield">
                        {{ field }}{% if field.errors %}<img src="''' + MEDIA_URL + '''icons/error.png" alt="error"/>{% endif %}
                        {{field.errors}}
                    </div>
                </li>''')
ERROR_NOTE_TEMPLATE = Template('''
    <p class="errorindicator">
        <img src="''' + MEDIA_URL + '''icons/exclamation.png" alt="exclamation" />
        Please correct the error below.
    </p>''')

@register.filter
def display_form(form):
    """
    Convert the form to HTML as we like it.
    """
    output = ["<ul>"]
    for field in form:
        c = Context({"field":field})
        output.append( FIELD_TEMPLATE.render(c) )

    output.append('<li><input class="submit" type="submit" value="Submit" /></li>\n</ul>')
    return mark_safe('\n'.join(output))

@register.filter
def error_note(form):
    """
    Display the pre-form note about errors (if any).
    """
    output = ""
    if form.errors:
        c = Context({})
        output = ERROR_NOTE_TEMPLATE.render(c)

    return mark_safe(output)


