from django import template
register = template.Library()

@register.filter
def default_bu(offering, posting):
    bu = posting.default_bu(offering)
    return bu