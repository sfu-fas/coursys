from django import template
register = template.Library()

from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.constants import PERMISSION_CHOICES
from faculty.models import EVENT_TYPES
import fractions

@register.filter
def get_config(event, field):
    if isinstance(event, CareerEventHandlerBase):
        return event.get_config(field, 'unknown')
    else:
        return event.config.get(field, 'unknown')


@register.filter
def get_display(handler, field):
    return handler.get_display(field)

@register.filter
def get_editor_role(event, editor):
    return PERMISSION_CHOICES[event.get_handler().permission(editor)]


@register.filter
def can_approve(person, event):
    return event.get_handler().can_approve(person)


@register.filter
def can_edit(person, event):
    return event.get_handler().can_edit(person)


@register.filter
def can_view(person, event):
    return event.get_handler().can_view(person)


class HandlerPermNode(template.Node):
    def __init__(self, handler, action, editor, person, varname):
        self.handler = template.Variable(handler)
        self.editor = template.Variable(editor)
        self.person = template.Variable(person)
        self.action = action
        self.varname = varname

    def get_permission(self, context):
        Handler = EVENT_TYPES.get(self.handler.resolve(context).upper())
        editor = self.editor.resolve(context)
        person = self.person.resolve(context)
        tmp = Handler.create_for(person)
        return getattr(tmp, "can_%s" % self.action)(editor)

    def render(self, context):
        context[self.varname] = self.get_permission(context)
        return ''


@register.tag
def can_view_handler(parser, token):
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("%s takes exactly 5 arguments" % bits[0])
    if bits[4] != "as":
        raise template.TemplateSyntaxError("%s argument 4 must be 'as'" % bits[0])
    return HandlerPermNode(bits[1], "view", bits[2], bits[3], bits[5])


@register.tag
def can_edit_handler(parser, token):
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("%s takes exactly 5 arguments" % bits[0])
    if bits[4] != "as":
        raise template.TemplateSyntaxError("%s argument 4 must be 'as'" % bits[0])
    return HandlerPermNode(bits[1], "edit", bits[2], bits[3], bits[5])


@register.tag
def can_approve_handler(parser, token):
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("%s takes exactly 5 arguments" % bits[0])
    if bits[4] != "as":
        raise template.TemplateSyntaxError("%s argument 4 must be 'as'" % bits[0])
    return HandlerPermNode(bits[1], "approve", bits[2], bits[3], bits[5])

@register.filter
def fraction_display(val):
    val = fractions.Fraction(val)
    n = val.numerator
    d = val.denominator

    if n != 0:
        whole = abs(n)/d*(n/abs(n)) # in case val is negative
    else:
        whole = 0
    res = str(whole)
    # only have a negative fraction if whole is 0
    if val<0 and whole==0:
        remainder = val + whole
    else:
        remainder = abs(val - whole)
    if remainder != 0:
        if whole == 0:
            res = str(remainder)
        else:
            res += ' ' + str(remainder)

    return res


@register.filter
def get_item(dictionary, key):
    """
    See: http://stackoverflow.com/questions/8000022/django-template-how-to-lookup-a-dictionary-value-with-a-variable
    """
    return dictionary.get(key)
