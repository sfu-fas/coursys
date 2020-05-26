from django import template
from django.urls.base import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe


register = template.Library()
STUDENT_TEMPLATE = """<a href="{url}">{fname} {lname}</a>"""


@register.filter
def student_submissions(member, activity):
    url = reverse('offering:quiz:submission_history', kwargs={
        'course_slug': activity.offering.slug,
        'activity_slug': activity.slug,
        'userid': member.person.userid_or_emplid()
    })
    context = {
        'url': url,
        'fname': escape(member.person.first_name),
        'lname': escape(member.person.last_name),
    }
    return mark_safe(STUDENT_TEMPLATE.format(**context))


@register.filter
def student_list(members, activity):
    member_links = (student_submissions(m, activity) for m in members)
    return mark_safe(', '.join(member_links))
