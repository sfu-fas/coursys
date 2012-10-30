import re
from django import template
from django.conf import settings
from coredata.models import Semester

numeric_test = re.compile("^\d+$")
register = template.Library()

# getattribute from http://snipt.net/Fotinakis/django-template-tag-for-dynamic-attribute-lookups/
# recursive idea from http://mousebender.wordpress.com/2006/11/10/recursive-getattrsetattr/
def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    # special cases
    if arg == 'application_status':
        return value.get_application_status_display()
    elif arg == 'senior_supervisors':
        sups = value.supervisor_set.filter(supervisor_type='SEN', removed=False)
        names = [s.sortname() for s in sups]
        if not sups:
            pot_sups = value.supervisor_set.filter(supervisor_type='POT', removed=False)
            names = [s.sortname()+"*" for s in pot_sups]
        return '; '.join(names)
    elif arg == 'supervisors':
        sups = value.supervisor_set.filter(supervisor_type__in=['SEN','COM'], removed=False)
        names = [s.sortname() for s in sups]
        return '; '.join(names)
    elif arg == 'completed_req':
        reqs = value.completedrequirement_set.all().select_related('requirement')
        return ', '.join(r.requirement.description for r in reqs)
    elif arg == 'current_status':
        return value.get_current_status_display()
    elif arg == 'active_semesters':
        return value.active_semesters_display()
    elif arg == 'gpa':
        res = value.person.gpa()
        if res:
            return res
        else:
            return ''
    elif arg == 'gender':
        return value.person.gender()
    elif arg == 'visa':
        return value.person.visa()
    elif arg == 'person.emplid':
        return unicode(value.person.emplid)

    elif '.' not in arg:
        if hasattr(value, str(arg)):
            res = getattr(value, arg)
        elif hasattr(value, 'has_key') and value.has_key(arg):
            res = value[arg]
        elif numeric_test.match(str(arg)) and len(value) > int(arg):
            res = value[int(arg)]
        else:
            res = settings.TEMPLATE_STRING_IF_INVALID
    else:
        L = arg.split('.')
        res = getattribute(getattr(value, L[0]), '.'.join(L[1:]))
    
    # force types to something displayable everywhere
    if isinstance(res, Semester):
        res = res.name
    elif res is None:
        res = ''
    elif type(res) not in [int, float, str, unicode]:
        res = unicode(res)
    
    return res

register.filter('getattribute', getattribute)

# Then, in template:
# {% load getattribute %}
# {{ object|getattribute:dynamic_string_var }}
