from django import template
register = template.Library()

from settings import MEDIA_URL
from django.template import Context, Template
from django.utils.safestring import mark_safe

@register.filter
def mobilize_url(url):
    """ Make sure URL has the prefix '/m' """
    if url[:3] != "/m/":
        return '/m' + url
    else:
        return url

@register.filter
def demobilize_url(url):
    """ Remove '/m' prefix in the url """
    if url[:3] == "/m/":
        return url[2:]
    else:
        return url
