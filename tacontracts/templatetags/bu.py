import decimal
from django import template

register = template.Library()

@register.filter
def bu(dec):
    if dec == "":
        return "0.00"
    else:
        return "%.2f" % dec
