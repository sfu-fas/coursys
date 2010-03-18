from django import template
register = template.Library()

from settings import MEDIA_URL
from django.template import Context, Template
from django.utils.safestring import mark_safe


FIELD_TEMPLATE = Template('''<li>
                    {{ field.label_tag }}
                    <div class="inputfield">
                        {{ field }}
			{% if field.errors %}<div class="errortext"><img src="''' + MEDIA_URL + '''icons/error.png" alt="error"/>&nbsp;{{field.errors.0}}</div>{% endif %}
			<div class="helptext">{{field.help_text}}</div>
                    </div>
                </li>''')
ERROR_NOTE_TEMPLATE = Template('''
    <p class="errorindicator">
        <img src="''' + MEDIA_URL + '''icons/exclamation.png" alt="exclamation" />
        Please correct the error below.
    </p>''')

@register.filter
def display_form(form, text="Submit"):
    """
    Convert the form to HTML as we like it.
    """
    output = ['<p class="requireindicator"><img src="/media//icons/required_star.gif" alt="required" />&nbsp;indicates required field</p>']
    output.append("<ul>")
    for field in form:
        c = Context({"field":field})
        output.append( FIELD_TEMPLATE.render(c) )
    
    output.append('<li><input class="submit" type="submit" value='+text+' /></li>\n</ul>')
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

FIELD_AS_TD_TEMPLATE = Template('''<td>
                           {% if field.errors %}
                           <div class="errortext"><img src="''' + MEDIA_URL + '''icons/error.png" alt="error"/>&nbsp;{{field.errors.0}}</div>
                           {% endif %}
                        {{ field }}
                </td>''')

@register.filter
def display_form_as_row(form, arg=None):
    """
    Convert the form to a HTML table row
    set arg to be "deleted_flag" to include the deleted field
    """    
    output = ["<tr>"]
    for field in form:
        if field.name == "deleted" and (arg != "deleted_flag"):
            continue
        c = Context({"field":field})
        output.append( FIELD_AS_TD_TEMPLATE.render(c))
    
    output.append("</tr>")    
    
    return mark_safe('\n'.join(output)) 

