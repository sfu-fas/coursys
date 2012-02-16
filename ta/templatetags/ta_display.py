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
