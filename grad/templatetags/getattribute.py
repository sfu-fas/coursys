import re
from django import template
from django.conf import settings

numeric_test = re.compile("^\d+$")
register = template.Library()

# getattribute from http://snipt.net/Fotinakis/django-template-tag-for-dynamic-attribute-lookups/
# recursive idea from http://mousebender.wordpress.com/2006/11/10/recursive-getattrsetattr/
def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if arg == 'application_status':
        return value.get_application_status_display()
    elif arg == 'current_status':
        return value.get_current_status_display()
    elif '.' not in arg:
        if hasattr(value, str(arg)):
            return getattr(value, arg)
        elif hasattr(value, 'has_key') and value.has_key(arg):
            return value[arg]
        elif numeric_test.match(str(arg)) and len(value) > int(arg):
            return value[int(arg)]
        else:
            return settings.TEMPLATE_STRING_IF_INVALID
    else:
        L = arg.split('.')
        return getattribute(getattr(value, L[0]), '.'.join(L[1:]))

register.filter('getattribute', getattribute)

# Then, in template:
# {% load getattribute %}
# {{ object|getattribute:dynamic_string_var }}
