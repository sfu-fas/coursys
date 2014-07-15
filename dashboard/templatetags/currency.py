import locale
import decimal
from django import template

register = template.Library()

@register.filter
def currency(i):
    try:
        return locale.currency(decimal.Decimal(i), grouping=True)
    except decimal.InvalidOperation:
        return locale.currency(0)
