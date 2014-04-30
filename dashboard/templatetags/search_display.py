from django import template
register = template.Library()

from dashboard.views import RESULT_TYPE_DISPLAY

@register.filter
def format_score(score):
    "A string-sortable version of the result.score"
    return "%07.2f" % (score,)

@register.filter
def display_type(ctype):
    "Display the result.content_type in a human-friendly way"
    return RESULT_TYPE_DISPLAY.get(ctype, ctype)