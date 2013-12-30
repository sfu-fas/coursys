from django import template
register = template.Library()

from django.conf import settings
from django.template import Context, Template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.core.urlresolvers import get_resolver, Resolver404
resolver = get_resolver(None)

@register.filter
def mobilize_url(url):
    """ Make sure URL has the prefix '/m' """
    if url[:3] != "/m/":
        murl = '/m' + url
    else:
        murl = url
    
    try:
        resolver.resolve(murl) # throws Resolver404 if can't resolve URL
        return murl
    except Resolver404:
        return url

@register.filter
def demobilize_url(url):
    """ Remove '/m' prefix in the url """
    if url[:3] == "/m/":
        return url[2:]
    else:
        return url

@register.filter
def mobile_link(url):
    murl = mobilize_url(url)
    try:
        resolver.resolve(murl) # throws Resolver404 if can't resolve URL
        return mark_safe('<a href="%s">mobile page</a>' % (escape(murl)))
    except Resolver404:
        return mark_safe('<a href="/m/">mobile site</a>')

