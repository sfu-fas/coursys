from django import template
from django.utils.safestring import mark_safe
from django.forms import ChoiceField, FileField
import collections

register = template.Library()


#"A filter to get component type"
#@register.filter()
#def get_component_type(component):
#    str = component.get_type()
#    return mark_safe(str)

# maybe not in use?
"A filter returns url"
@register.filter()
def get_url(item):
    return mark_safe(item.get_url())


# filter to display value of field from http://code.djangoproject.com/ticket/10427
@register.filter(name='field_value')
def field_value(field):
	""" 
	Returns the value for this BoundField, as rendered in widgets. 
	""" 
	if field.form.is_bound: 
		if isinstance(field.field, FileField) and field.data is None: 
			val = field.form.initial.get(field.name, field.field.initial) 
		else: 
			val = field.data 
	else:
		val = field.form.initial.get(field.name, field.field.initial)
		if isinstance(val, collections.Callable):
			val = val()
	if val is None:
		val = ''
	return val

@register.filter(name='display_value')
def display_value(field): 
	""" 
	Returns the displayed value for this BoundField, as rendered in widgets. 
	""" 
	value = field_value(field)
	if isinstance(field.field, ChoiceField): 
		for (val, desc) in field.field.choices: 
			if val == value: 
				return desc 
	return value