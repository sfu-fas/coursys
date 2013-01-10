from django import template
register = template.Library()
import decimal, locale
from django.utils.safestring import mark_safe
locale.setlocale( locale.LC_ALL, 'en_CA.UTF-8' )

@register.filter
def display_required_bu(offering, posting):
    return "%.2f" % (posting.required_bu(offering, count=offering.enrl_tot))

@register.filter
def display_extra_bu(offering, posting):
    return "%.2f" % offering.extra_bu() 

@register.filter
def display_bu_cap(offering, posting):
    return "%.2f" % (posting.required_bu(offering, count=offering.enrl_cap))

@register.filter
def display_assigned_bu(offering, posting):
    return "%.2f" % (posting.assigned_bu(offering))

@register.filter
def display_default_bu(offering, posting):
    return "%.2f" % (posting.default_bu(offering, count=offering.enrl_tot))

@register.filter
def display_default_bu_cap(offering, posting):
    return "%.2f" % (posting.default_bu(offering, count=offering.enrl_cap))

@register.filter
def display_bu_difference(offering, posting):
    required = posting.required_bu(offering)
    assigned = posting.assigned_bu(offering)
    diff = assigned-required
    if diff < -0.01:
        return mark_safe('<span class="over">%.2f</span>' % (diff))
    elif diff > 0.01:
        return mark_safe('<span class="under">+%.2f</span>' % (diff))
    return mark_safe("<span>%.2f</span>" % (abs(diff)))

@register.filter
def display_applicant_count(offering, posting):
    return posting.applicant_count(offering)

@register.filter
def display_total_pay(offering, posting):
    amt = locale.currency(float(posting.total_pay(offering)))
    return '%s' % (amt)

@register.filter
def display_all_total_pay(val):
    amt = locale.currency(float(val))
    return '%s' % (amt)

@register.filter
def display_ta_count(offering, posting):
    return posting.ta_count(offering)
