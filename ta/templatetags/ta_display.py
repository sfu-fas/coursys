from django import template
register = template.Library()
import decimal

@register.filter
def display_bu(offering, posting):
    default = posting.default_bu(offering)
    extra = offering.extra_bu()
    if extra == decimal.Decimal(0):
        return "%.2f" % (default)
    elif extra > decimal.Decimal(0):
        return "%.2f + %.2f = %.2f" % (default, extra, default+extra)
    else:
        return "%.2f - %.2f = %.2f" % (default, -extra, default+extra)

@register.filter
def display_assigned_bu(offering, posting):
    return "%.2f" % (posting.assigned_bu(offering))

@register.filter
def display_bu_difference(offering, posting):
    required = posting.required_bu(offering)
    assigned = posting.assigned_bu(offering)
    return "%.2f" % (required-assigned)

@register.filter
def display_applicant_count(offering, posting):
    return posting.applicant_count(offering)
