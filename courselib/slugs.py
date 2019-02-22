import unidecode, re
from django.template.defaultfilters import slugify

def make_slug(txt):
    """
    Turn this string into a slug the way we want it done here.
    """
    return slugify(unidecode.unidecode(str(txt).lower()))

