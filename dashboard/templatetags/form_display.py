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
def as_dl(form, safe=False, excludefields=[], includefields=None, formclass='dlform'):
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

        reqtext = ''
        if field.field.required:
            #reqtext = ' <span class="required">*</span>'
            reqtext = '&nbsp;' + required_icon
            reqcount += 1
        
        if field.label:
            labelid = str(field.name)
            if form.prefix:
                labelid = form.prefix + '-' + labelid
            if isinstance(field.field.widget, (RadioSelect, SupervisorWidget)):
                labelid += '_0'
            out.append('<dt><label for="id_%s">%s:%s</label></dt><dd>' % (labelid, escape(field.label), reqtext))
        
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
        out.append('</dd>')
    
    out.append('</dl>')
    if reqcount > 0:
        out.append('<p class="helptext">' + required_icon + ' This field is required.</p>')
    return mark_safe('\n'.join(out))


@register.filter
def as_dl_2(form, safe=False):
    """
    Output a Form as a nice <dl>
    """
    out = []
    out.append(unicode(form.non_field_errors()))
    if form.hidden_fields():
        out.append('<div style="display:none">')
        for field in form.hidden_fields():
            out.append(unicode(field))
        out.append('</div>')
        
    out.append('<dl class="dlform">')
    reqcount = 0
    for field in form.visible_fields():
        reqtext = ''
        if field.field.required:
            reqtext = ' <span class="required">*</span>'
            reqcount += 1
        labelid = field.name
        if form.prefix:
            labelid = form.prefix + '-' + labelid
        out.append('<dt><label for="id_%s">%s:%s</label></dt><dd>' % (labelid, escape(field.label), reqtext))
        out.append('<div class="field">%s</div>' % (unicode(field)))
        if field.help_text and not isinstance(field.help_text, Promise): # we don't have translations: if exists, it's the default:
            if safe:
                out.append('<div class="helptext">%s</div>' % (field.help_text))
            else:
                out.append('<div class="helptext">%s</div>' % (escape(field.help_text)))
        if field.errors:
            out.append(unicode(field.errors))
        out.append('</dd>')
    
    out.append('</dl>')
    if reqcount > 0:
        out.append('<p class="helptext"><span class="required">*</span> This field is required.</p>')
    return mark_safe('\n'.join(out))

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
def required_label(label):
    """
    Style label as it should be if on a required field.
    """
    return mark_safe(escape(label) + '&nbsp;' + required_icon)
