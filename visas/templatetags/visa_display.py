from django import template
from visas.models import Visa
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as e
register = template.Library()


@register.filter
def display_visas(person):
    visas = Visa.get_visas([person])
    if visas.count() > 1:
        result = '<a href="%s">More than one visa found</a>' % reverse('visas:list_all_visas', kwargs={'emplid':person.userid_or_emplid()})
        return mark_safe(result)

    elif visas.count() == 0:
        result = '<a href="%s">No visa found</a>' % reverse('visas:new_visa', kwargs={'emplid':person.userid_or_emplid()})
        return mark_safe(result)

    elif visas.count() == 1:
        visa = visas[0]

        result = ['<a href="', reverse('visas:edit_visa', kwargs={'visa_id': visa.id}), '" ',
                  e(add_visa_display_class(visa)),'>', e(visa.status),' valid from ', e(str(visa.start_date)), ' until ',
                  e(str(visa.end_date)), ' -- ', e(visa.get_validity()), '</a>']
        return mark_safe(''.join(result))

    else:
        return "Undefined visa error, please contact support."

@register.filter
def add_visa_display_class(visa):
    if visa.is_expired():
        return 'class=visaexpired'
    elif visa.is_almost_expired():
        return 'class=visaalmostexpired'
    elif visa.is_valid():
        return 'class=visavalid'
    else:
        return ""
