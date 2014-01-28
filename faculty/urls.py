from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, UNIT_SLUG

FACULTY_SLUG = UNIT_SLUG + '/' + USERID_OR_EMPLID

urlpatterns = patterns('',
    url(r'^$', 'faculty.views.index'),
    url(r'^memo-templates$', 'faculty.views.memo_templates', name="template_index"),
    url(r'^memo-templates/new$', 'faculty.views.new_memo_template', name="faculty_create_template"),
    url(r'^memo-templates/(?P<slug>[^//]+)/manage$', 'faculty.views.manage_memo_template', name="faculty_manage_template"),
    url(r'^' + USERID_OR_EMPLID + '/summary$', 'faculty.views.summary', name="faculty_summary"),
    url(r'^' + USERID_OR_EMPLID + '/otherinfo$', 'faculty.views.otherinfo', name="faculty_otherinfo"),
    url(r'^' + USERID_OR_EMPLID + '/new-event$', 'faculty.views.create_event', name="faculty_create_event"),
    url(r'^' + USERID_OR_EMPLID + '/(?P<slug>[^//]+)/change$', 'faculty.views.change_event', name="faculty_change_event"),
)
