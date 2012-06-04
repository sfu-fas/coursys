from django import template
from django.core import paginator
from django.template.context import Context
from django.template.loader import get_template

register = template.Library()

@register.filter()
def create_pagination(element):
    """
    Creates the navigation for a Paginator Page object
    """
    if not type(element) is paginator.Page:
        raise TypeError("Element isn't of type 'Paginator Page'")
    template = get_template('discuss/pagination.html')
    return template.render(Context({'page': element}))
