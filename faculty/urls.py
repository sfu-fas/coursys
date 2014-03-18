from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE, UNIT_SLUG

EVENT_SLUG = '(?P<event_slug>' + SLUG_RE + ')'
EVENT_PREFIX = USERID_OR_EMPLID + '/events/' + EVENT_SLUG
GRANT_SLUG = '(?P<grant_slug>' + SLUG_RE + ')'


urlpatterns = patterns('',
    url(r'^$', 'faculty.views.index'),
    url(r'^search$', 'faculty.views.search_index'),
    url(r'^search/(?P<event_type>{})$'.format(SLUG_RE), 'faculty.views.search_events'),
    url(r'^salaries$', 'faculty.views.salary_index'),
    url(r'^salaries/' + USERID_OR_EMPLID + '$', 'faculty.views.salary_summary'),
    url(r'^queue/$', 'faculty.views.status_index', name="status_index"),

    # Report: Available Teaching Capacity
    url(r'^report/teaching_capacity$', 'faculty.views.teaching_capacity'),
    url(r'^report/teaching_capacity.csv$', 'faculty.views.teaching_capacity_csv'),

    # Report: Courses + Instructor Accreditation
    url(r'^report/course_accreditation$', 'faculty.views.course_accreditation'),
    url(r'^report/course_accreditation.csv$', 'faculty.views.course_accreditation_csv'),

    url(r'^event-management$', 'faculty.views.manage_event_index', name="faculty_events_manage_index"),
    url(r'^event-management/(?P<event_type>' + SLUG_RE + ')/memo-templates$', 'faculty.views.memo_templates', name="template_index"),
    url(r'^event-management/(?P<event_type>' + SLUG_RE + ')/memo-templates/new$', 'faculty.views.new_memo_template', name="faculty_create_template"),
    url(r'^event-management/(?P<event_type>' + SLUG_RE + ')/memo-templates/(?P<slug>' + SLUG_RE + ')/manage$', 'faculty.views.manage_memo_template', name="faculty_manage_template"),
    url(r'^' + USERID_OR_EMPLID + '/summary$', 'faculty.views.summary', name="faculty_summary"),
    url(r'^' + USERID_OR_EMPLID + '/teaching_summary$', 'faculty.views.teaching_summary', name="faculty_teaching_summary"),
    url(r'^' + USERID_OR_EMPLID + '/study_leave_credits$', 'faculty.views.study_leave_credits', name="faculty_study_leave_credits"),
    url(r'^' + USERID_OR_EMPLID + '/otherinfo$', 'faculty.views.otherinfo', name="faculty_otherinfo"),
    url(r'^' + USERID_OR_EMPLID + '/new-event$', 'faculty.views.event_type_list', name="faculty_event_types"),
    url(r'^' + USERID_OR_EMPLID + '/new-event/(?P<event_type>' + SLUG_RE + ')$', 'faculty.views.create_event', name="faculty_create_event"),

    # Faculty Person Timeline
    url(r'^' + USERID_OR_EMPLID + '/timeline$', 'faculty.views.timeline'),
    url(r'^' + USERID_OR_EMPLID + '/timeline.json$', 'faculty.views.timeline_json'),

    url(r'^' + EVENT_PREFIX + '/$', 'faculty.views.view_event', name="faculty_event_view"),
    url(r'^' + EVENT_PREFIX + '/change$', 'faculty.views.change_event', name="faculty_change_event"),
    url(r'^' + EVENT_PREFIX + '/change-status$', 'faculty.views.change_event_status', name="faculty_change_event_status"),
    url(r'^' + EVENT_PREFIX + '/attach$', 'faculty.views.new_attachment', name="faculty_add_attachment"),
    url(r'^' + EVENT_PREFIX + '/attach/(?P<attach_slug>' + SLUG_RE + ')/view$', 'faculty.views.view_attachment', name="faculty_view_attachment"),
    url(r'^' + EVENT_PREFIX + '/attach/(?P<attach_slug>' + SLUG_RE + ')/download$', 'faculty.views.download_attachment', name="faculty_download_attachment"),
    url(r'^' + EVENT_PREFIX + '/(?P<memo_template_slug>' + SLUG_RE + ')' + '/new$', 'faculty.views.new_memo', name="faculty_event_memo_create"),
    url(r'^' + EVENT_PREFIX + '/(?P<memo_slug>' + SLUG_RE + ')' + '/manage$', 'faculty.views.manage_memo', name="faculty_event_memo_manage"),
    url(r'^' + EVENT_PREFIX + '/_get_text/(?P<memo_template_id>' + SLUG_RE + ')' + '$', 'faculty.views.get_memo_text', name="faculty_event_memo_manage"),
    url(r'^' + EVENT_PREFIX + '/(?P<memo_slug>' + SLUG_RE + ')' + '$', 'faculty.views.get_memo_pdf', name="faculty_event_memo_pdf"),
    url(r'^' + EVENT_PREFIX + '/(?P<memo_slug>' + SLUG_RE + ')' + '/view$', 'faculty.views.view_memo', name="faculty_event_view_memo"),
    url(r'^grants$', 'faculty.views.grant_index', name="grants_index"),
    url(r'^grants/new$', 'faculty.views.new_grant', name="new_grant"),
    url(r'^grants/convert/(?P<gid>\d+)$', 'faculty.views.convert_grant', name="convert_grant"),
    url(r'^grants/delete/(?P<gid>\d+)$', 'faculty.views.delete_grant', name="delete_grant"),
    url(r'^grants/import$', 'faculty.views.import_grants', name="import_grants"),
    url(r'^grants/' + UNIT_SLUG + '/' + GRANT_SLUG + '$', 'faculty.views.view_grant', name="view_grant"),
    
)
