from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

#FACULTY_SLUG = UNIT_SLUG + '/' + USERID_OR_EMPLID
EVENT_SLUG = '(?P<event_slug>' + SLUG_RE + ')'


urlpatterns = patterns('',
    url(r'^$', 'faculty.views.index'),
    url(r'^memo-templates$', 'faculty.views.memo_templates', name="template_index"),
    url(r'^memo-templates/new$', 'faculty.views.new_memo_template', name="faculty_create_template"),
    url(r'^memo-templates/(?P<slug>' + SLUG_RE + ')/manage$', 'faculty.views.manage_memo_template', name="faculty_manage_template"),
    url(r'^' + USERID_OR_EMPLID + '/summary$', 'faculty.views.summary', name="faculty_summary"),
    url(r'^' + USERID_OR_EMPLID + '/career_events$', 'faculty.views.events_list', name="faculty_events_list"),
    url(r'^' + USERID_OR_EMPLID + '/otherinfo$', 'faculty.views.otherinfo', name="faculty_otherinfo"),
    url(r'^' + USERID_OR_EMPLID + '/new-event$', 'faculty.views.event_type_list', name="faculty_event_types"),
    url(r'^' + USERID_OR_EMPLID + '/new-event/(?P<handler>[a-z]+)$', 'faculty.views.create_event', name="faculty_create_event"),
    url(r'^' + USERID_OR_EMPLID + '/events/' + EVENT_SLUG + '/change$', 'faculty.views.change_event', name="faculty_change_event"),
)
