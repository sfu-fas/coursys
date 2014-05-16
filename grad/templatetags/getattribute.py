from django import template

register = template.Library()

from grad.forms import getattribute
register.filter('getattribute', getattribute)

# Then, in template:
# {% load getattribute %}
# {{ object|getattribute:dynamic_string_var }}
