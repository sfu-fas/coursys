from django import template
register = template.Library()
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape
from django.utils.functional import Promise
from django.forms.widgets import RadioSelect
from grad.forms import SupervisorWidget

required_icon = '<i class="reqicon fa fa-star-o"></i>'

@register.filter
def field_display(field, safe=False):
    out = []
    if isinstance(field.field.widget, (forms.widgets.RadioSelect, forms.widgets.CheckboxSelectMultiple)):
        out.append('<div class="field radio">%s</div>' % (unicode(field)))
    else:
        out.append('<div class="field">%s</div>' % (unicode(field)))
    out.append(unicode(field.errors))

    if field.help_text and not isinstance(field.help_text, Promise): # we don't have translations: if exists, it's the default
        if safe:
            out.append('<div class="helptext">%s</div>' % (field.help_text))
        else:
            out.append('<div class="helptext">%s</div>' % (escape(field.help_text)))
    return mark_safe('\n'.join(out))


@register.filter
def label_display(field, prefix=''):
    out = []

    labelid = str(field.name)
    if prefix:
        labelid = prefix + '-' + labelid
    if isinstance(field.field.widget, (RadioSelect, SupervisorWidget)):
        labelid += '_0'

    out.append('<label for="id_%s">' % (labelid,))
    out.append(escape(field.label))
    out.append(':')
    if field.field.required:
        out.append('&nbsp;' + required_icon)

    out.append('</label>')

    return mark_safe(''.join(out))


@register.filter
def as_dl(form, safe=False, excludefields=[], includefields=None, formclass='dlform', reqmessage=True):
    """
    Output a Form as a nice <dl>
    """
    out = []
    out.append(unicode(form.non_field_errors()))
    if form.hidden_fields():
        out.append('<div style="display:none">')
        for field in form.hidden_fields():
            if field.name in excludefields or (
                    includefields is not None and field.name not in includefields) :
                continue
            out.append(unicode(field))
        out.append('</div>')
        
    out.append('<dl class="%s">' % (formclass))
    reqcount = 0
    for field in form.visible_fields():
        if field.name in excludefields or (
                includefields is not None and field.name not in includefields) :
            continue

        if field.field.required:
            reqcount += 1
        
        if field.label:
            out.append('<dt>%s</dt>' % (label_display(field, form.prefix)))

        out.append('<dd>')
        out.append(field_display(field, safe=safe))
        out.append('</dd>')
    
    out.append('</dl>')
    if reqmessage and reqcount > 0:
        out.append(required_message(None))
    return mark_safe('\n'.join(out))


@register.filter
def required_label(label):
    """
    Style label as it should be if on a required field.
    """
    return mark_safe(escape(label) + '&nbsp;' + required_icon)

@register.filter
def required_message(_):
    return mark_safe('<p class="helptext">' + required_icon + ' This field is required.</p>')





# various permutations of the as_dl arguments that are needed around the system...

@register.filter
def as_dl_safe(form):
    """
    Like as_dl, but assumes helptext is a safe string
    """
    return as_dl(form, safe=True)

@register.filter
def as_dl_excludefields(form, excl):
    """
    Like as_dl, but allows excluding some fields with filter argument
    """
    excllist = excl.split(',')
    return as_dl(form, excludefields=excllist)

@register.filter
def as_dl_includefields(form, incl):
    """
    Like as_dl, but allows including some fields with filter argument
    Hide helptext
    """
    if isinstance(incl, list):
        incllist = incl
    else:
        incllist = incl.split(',')
    return as_dl(form, includefields=incllist)

@register.filter
def as_dl_onlineforms(form):
    return as_dl(form)
    #return as_dl(form, formclass="onlineform")


@register.filter
def as_dl_noreq(form):
    return as_dl(form, reqmessage=False)

@register.filter
def as_dl_inline(form):
    return as_dl(form, formclass='dlform inline', reqmessage=False)