import unidecode, re
from django.template.defaultfilters import slugify

def make_slug(txt):
    """
    Turn this string into a slug the way we want it done here.
    """
    return slugify(unidecode.unidecode(str(txt).lower()))

def coursename_by_slug(slug):
    start = slug.find('-')+1
    if slug[-2:] == '00':
        coursename = slug.upper()[start:].replace("-", " ")[:-2]
    else:
        coursename = slug.upper()[start:].replace("-", " ")

    return coursename