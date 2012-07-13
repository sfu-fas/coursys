from django import template
register = template.Library()

@register.filter
def floatsortable(value):
    """
    floating point value in a sortable way
    """
    return "%012.2f" % (value)
