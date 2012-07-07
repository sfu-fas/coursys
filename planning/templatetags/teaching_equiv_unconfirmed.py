from django import template
from coredata.models import Person
from planning.models import TeachingEquivalent
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def unconfirmed_count(value):
    """
    Number of unconfirmed teaching equivalents for a instructor
    """
    if not isinstance(value, Person):
        raise ValueError("Value must be a person")
    count = len(TeachingEquivalent.objects.filter(instructor=value, status='UNCO'))
    if count is 0:
        return mark_safe('--')
    else:
        return mark_safe(count)