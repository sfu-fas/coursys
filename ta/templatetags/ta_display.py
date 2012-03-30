from django import template
register = template.Library()
import decimal, locale
from django.utils.safestring import mark_safe
locale.setlocale( locale.LC_ALL, '' )

def _bu_display(offering, posting, count):
    default = posting.default_bu(offering, count=count)
    extra = offering.extra_bu()
    if extra == decimal.Decimal(0):
        return "%.2f" % (default)
    elif extra > decimal.Decimal(0):
        return "%.2f + %.2f = %.2f" % (default, extra, default+extra)
    else:
        return "%.2f - %.2f = %.2f" % (default, -extra, default+extra)

@register.filter
def display_bu(offering, posting):
    return _bu_display(offering, posting, count=offering.enrl_tot)

@register.filter
def display_bu_cap(offering, posting):
    return _bu_display(offering, posting, count=offering.enrl_cap)

@register.filter
def display_assigned_bu(offering, posting):
    return "%.2f" % (posting.assigned_bu(offering))

@register.filter
def display_bu_difference(offering, posting):
    required = posting.required_bu(offering)
    assigned = posting.assigned_bu(offering)
    diff = required-assigned
    if diff < 0:
        return mark_safe('<span class="over">%.2f</span>' % (diff))
    elif diff > 0:
        return mark_safe('<span class="under">%.2f</span>' % (diff))
    return mark_safe("<span>%.2f</span>" % (diff))

@register.filter
def display_applicant_count(offering, posting):
    return posting.applicant_count(offering)

@register.filter
def display_campus_preference(campus_preferences, index):
    return campus_preferences[index].get_pref_display()

@register.filter
def display_course_rank(course_preferences, index):
    return course_preferences[index].rank

@register.filter
def display_total_pay(offering, posting):
    amt = locale.currency(float(posting.total_pay(offering)))
    return mark_safe('<strong>%s</strong>' % (amt)) 

@register.filter
def display_all_total_pay(val):
    amt = locale.currency(float(val))
    return mark_safe('<strong>%s</strong>' % (amt)) 

@register.filter
def display_ta_count(offering, posting):
    return posting.ta_count(offering)