from django import template
register = template.Library()


from django.conf import settings
STATIC_URL = settings.STATIC_URL
from django.template import Context, Template
from django.utils.safestring import mark_safe
from django.utils.functional import SimpleLazyObject


ERROR_NOTE_TEMPLATE = SimpleLazyObject(lambda: Template('''
    <p class="errorindicator">
        <img src="''' + STATIC_URL + '''icons/exclamation.png" alt="exclamation" />
        Please correct the error below.
    </p>'''))


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

FIELD_AS_TD_TEMPLATE = SimpleLazyObject(lambda: Template('''<td>
                           {% if field.errors %}
                           <div class="errortext">{{field.errors.0}}</div>
                           {% endif %}
                        {{ field }}
                </td>'''))
FIELD_AS_TD_TEMPLATE_HIDDEN = SimpleLazyObject(lambda: Template('<td class="hidden">{{ field }}</td>'))

@register.filter
def display_form_as_row(form, arg=None):
    """
    Convert the form to a HTML table row
    set arg to be "deleted_flag" to include the deleted field
    """
    output = ["<tr>"]
    if arg == 'hidden':
        output = ['<tr class="hidden">']
    for field in form.visible_fields():
        if field.name == "deleted" and (arg != "deleted_flag"):
            output.append("<td></td>")
            continue
        c = Context({"field":field})
        output.append( FIELD_AS_TD_TEMPLATE.render(c))
    
    for field in form.hidden_fields():
        c = Context({"field":field})
        output.append( FIELD_AS_TD_TEMPLATE_HIDDEN.render(c))
    
    output.append("</tr>")
    
    return mark_safe('\n'.join(output)) 


# from http://stackoverflow.com/questions/35948/django-templates-and-variable-attributes
from django.template import Variable, VariableDoesNotExist
@register.filter
def hash(object, attr):
    pseudo_context = { 'object' : object }
    try:
        value = Variable('object.%s' % attr).resolve(pseudo_context)
    except VariableDoesNotExist:
        value = None
    return value
