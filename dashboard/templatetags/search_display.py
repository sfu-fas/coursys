from django.utils.safestring import mark_safe
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

STARS = 5
@register.filter
def score_stars(score, maxscore):
    """
    Turn the results score into 5 stars out of the max
    """
    stars = 1.0 * STARS * score/maxscore
    wholestars = int(stars)

    frac = stars - wholestars
    if frac >= 0.5:
        halfstars = 1
    else:
        halfstars = 0

    return mark_safe(
        wholestars * '<i class="fa fa-star"></i>'
        + halfstars * '<i class="fa fa-star-half-o"></i>'
        + (STARS - wholestars - halfstars) * '<i class="fa fa-star-o"></i>'
    )
