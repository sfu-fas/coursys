from django.urls import include, re_path as url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE, UNIT_SLUG, COURSE_SLUG
import faculty.views as faculty_views

EVENT_TYPE = '(?P<event_type>' + SLUG_RE + ')'
EVENT_SLUG = '(?P<event_slug>' + SLUG_RE + ')'
GRANT_SLUG = '(?P<grant_slug>' + SLUG_RE + ')'
ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'

event_patterns = [ # prefix: /faculty/USERID_OR_EMPLID/events/EVENT_SLUG/
    url(r'^$', faculty_views.view_event, name='view_event'),
    url(r'^change$', faculty_views.change_event, name='change_event'),
    url(r'^change-status$', faculty_views.change_event_status, name='change_event_status'),
    url(r'^attach$', faculty_views.new_attachment, name='new_attachment'),
    url(r'^attach-text$', faculty_views.new_text_attachment, name='new_text_attachment'),
    url(r'^attach/(?P<attach_slug>' + SLUG_RE + ')/view$', faculty_views.view_attachment, name='view_attachment'),
    url(r'^attach/(?P<attach_slug>' + SLUG_RE + ')/download$', faculty_views.download_attachment, name='download_attachment'),
    url(r'^attach/(?P<attach_slug>' + SLUG_RE + ')/delete$', faculty_views.delete_attachment, name='delete_attachment'),
    url(r'^(?P<memo_template_slug>' + SLUG_RE + ')' + '/new$', faculty_views.new_memo, name='new_memo'),
    url(r'^new-memo$', faculty_views.new_memo_no_template, name='new_memo_no_template'),
    url(r'^(?P<memo_slug>' + SLUG_RE + ')' + '/manage$', faculty_views.manage_memo, name='manage_memo'),
    url(r'^_get_text/(?P<memo_template_id>' + SLUG_RE + ')' + '$', faculty_views.get_memo_text, name='get_memo_text'),
    url(r'^(?P<memo_slug>' + SLUG_RE + ')' + '$', faculty_views.get_memo_pdf, name='get_memo_pdf'),
    url(r'^(?P<memo_slug>' + SLUG_RE + ')' + '/view$', faculty_views.view_memo, name='view_memo'),
    url(r'^(?P<memo_slug>' + SLUG_RE + ')' + '/delete$', faculty_views.delete_memo, name='delete_memo'),
    url(r'^generate_pdf/(?P<pdf_key>' + SLUG_RE + ')' + '$', faculty_views.generate_pdf, name='generate_pdf')
]

faculty_member_patterns = [ # prefix: /faculty/USERID_OR_EMPLID/
    # Person Specific Actions
    url(r'^summary$', faculty_views.summary, name='summary'),
    url(r'^setup$', faculty_views.faculty_wizard, name='faculty_wizard'),
    url(r'^setup/(?P<position>\d+)$', faculty_views.faculty_wizard, name='faculty_wizard'),
    url(r'^otherinfo$', faculty_views.otherinfo, name='otherinfo'),
    url(r'^new-event$', faculty_views.event_type_list, name='event_type_list'),
    url(r'^new-event/(?P<event_type>' + SLUG_RE + ')$', faculty_views.create_event, name='create_event'),
    url(r'^setup/pick_position$', faculty_views.pick_position, name='pick_position'),

    url(r'^timeline$', faculty_views.timeline, name='timeline'),
    url(r'^timeline.json$', faculty_views.timeline_json, name='timeline_json'),

    url(r'^contact-info$', faculty_views.faculty_member_info, name='faculty_member_info'),
    url(r'^contact-info/edit$', faculty_views.edit_faculty_member_info, name='edit_faculty_member_info'),

    url(r'^teaching_credit_override/' + COURSE_SLUG + '$', faculty_views.teaching_credit_override, name='teaching_credit_override'),
    url(r'^salary$', faculty_views.salary_summary, name='salary_summary'),

    # Report:Teaching Summary
    url(r'^teaching_summary$', faculty_views.teaching_summary, name='teaching_summary'),
    url(r'^teaching_summary.csv$', faculty_views.teaching_summary_csv, name='teaching_summary_csv'),

    # Report: Study Leave Credits
    url(r'^study_leave_credits$', faculty_views.study_leave_credits, name='study_leave_credits'),
    url(r'^study_leave_credits.csv$', faculty_views.study_leave_credits_csv, name='study_leave_credits_csv'),

    # Event Specific Actions
    url(r'^events/' + EVENT_SLUG + '/', include(event_patterns)),
]

faculty_patterns = [ # prefix: /faculty/
    # Top Level Stuff
    url(r'^$', faculty_views.index, name='index'),
    url(r'^queue$', faculty_views.status_index, name='status_index'),
    url(r'^members$', faculty_views.manage_faculty_roles, name='manage_faculty_roles'),

    # Event Searching
    url(r'^search/$', faculty_views.search_index, name='search_index'),
    url(r'^search/' + EVENT_TYPE + '$', faculty_views.search_events, name='search_events'),

    # Report: Salary
    url(r'^salaries$', faculty_views.salary_index, name='salary_index'),
    url(r'^salaries.csv$', faculty_views.salary_index_csv, name='salary_index_csv'),

    # Report: Fallout
    url(r'^fallout$', faculty_views.fallout_report, name='fallout_report'),
    url(r'^fallout.csv$', faculty_views.fallout_report_csv, name='fallout_report_csv'),

    # Report: Available Teaching Capacity
    url(r'^report/teaching_capacity$', faculty_views.teaching_capacity, name='teaching_capacity'),
    url(r'^report/teaching_capacity.csv$', faculty_views.teaching_capacity_csv, name='teaching_capacity_csv'),

    # Report: Courses + Instructor Accreditation
    url(r'^report/course_accreditation$', faculty_views.course_accreditation, name='course_accreditation'),
    url(r'^report/course_accreditation.csv$', faculty_views.course_accreditation_csv, name='course_accreditation_csv'),

    # Event Management
    url(r'^event-management$', faculty_views.manage_event_index, name='manage_event_index'),
    url(r'^event-management/' + EVENT_TYPE + '/$', faculty_views.event_config, name='event_config'),
    url(r'^event-management/' + EVENT_TYPE + '/new-memo$', faculty_views.new_memo_template, name='new_memo_template'),
    url(r'^event-management/' + EVENT_TYPE + '/memos/(?P<slug>' + SLUG_RE + ')/manage$', faculty_views.manage_memo_template, name='manage_memo_template'),
    url(r'^event-management/' + EVENT_TYPE + '/new-config$', faculty_views.event_config_add, name='event_config_add'),
    #url(r'^event-management/' + EVENT_TYPE + '/memo-templates/(?P<unit>\w+)/(?P<flag>\w+)/delete-flag$', faculty_views.delete_event_flag, name='delete_event_flag', name="faculty_delete_flag"),

    # Grant Stuff
    url(r'^grants/$', faculty_views.grant_index, name='grant_index'),
    #url(r'^grants/new$', faculty_views.new_grant, name='new_grant', name="new_grant"),
    url(r'^grants/convert/(?P<gid>\d+)$', faculty_views.convert_grant, name='convert_grant'),
    url(r'^grants/delete/(?P<gid>\d+)$', faculty_views.delete_grant, name='delete_grant'),
    url(r'^grants/import$', faculty_views.import_grants, name='import_grants'),
    url(r'^grants/' + UNIT_SLUG + '/' + GRANT_SLUG + '$', faculty_views.view_grant, name='view_grant'),
    url(r'^grants/' + UNIT_SLUG + '/' + GRANT_SLUG + '/edit$', faculty_views.edit_grant, name='edit_grant'),

    # faculty-member hierarchy
    url(r'^' + USERID_OR_EMPLID + '/', include(faculty_member_patterns)),

    # Positions
    url(r'^positions/$', faculty_views.list_positions, name='list_positions'),
    url(r'^positions/new_position$', faculty_views.new_position, name='new_position'),
    url(r'^positions/(?P<position_id>\d+)/edit_position/$', faculty_views.edit_position, name='edit_position'),
    url(r'^positions/(?P<position_id>\d+)/delete_position/$', faculty_views.delete_position, name='delete_position'),
    url(r'^positions/(?P<position_id>\d+)/view_position/$', faculty_views.view_position, name='view_position'),
    url(r'^positions/(?P<position_id>\d+)/assign_position_entry/$', faculty_views.assign_position_entry, name='assign_position_entry'),
    url(r'^positions/(?P<position_id>\d+)/assign_position_person/$', faculty_views.assign_position_person, name='assign_position_person'),
    url(r'^positions/(?P<position_id>\d+)/assign_position_futureperson/$', faculty_views.assign_position_futureperson, name='assign_position_futureperson'),
    url(r'^positions/(?P<position_id>\d+)/add_position_credentials/$', faculty_views.position_add_credentials, name='position_add_credentials'),
    url(r'^positions/(?P<position_id>\d+)/yellow1/$', faculty_views.position_get_yellow_form_tenure, name='position_get_yellow_form_tenure'),
    url(r'^positions/(?P<position_id>\d+)/yellow2/$', faculty_views.position_get_yellow_form_limited, name='position_get_yellow_form_limited'),
    url(r'^positions/(?P<position_id>\d+)/new_attach', faculty_views.new_position_attachment, name='new_position_attachment'),
    url(r'^positions/(?P<position_id>\d+)/' + ATTACH_SLUG + '/delete$', faculty_views.delete_position_attachment, name='delete_position_attachment'),
    url(r'^positions/(?P<position_id>\d+)/' + ATTACH_SLUG + '/view', faculty_views.view_position_attachment, name='view_position_attachment'),
    url(r'^positions/(?P<position_id>\d+)/' + ATTACH_SLUG + '/download$', faculty_views.download_position_attachment, name='download_position_attachment'),


    # Future Person Management
    url(r'^(?P<futureperson_id>\d+)/edit_futureperson/$', faculty_views.edit_futureperson, name='edit_futureperson'),
    url(r'^(?P<futureperson_id>\d+)/edit_futureperson/(?P<from_admin>\d)/$', faculty_views.edit_futureperson, name='edit_futureperson'),
    url(r'^(?P<futureperson_id>\d+)/view_futureperson/$', faculty_views.view_futureperson, name='view_futureperson'),
    url(r'^(?P<futureperson_id>\d+)/view_futureperson/(?P<from_admin>\d)/$', faculty_views.view_futureperson, name='view_futureperson'),
    url(r'^(?P<futureperson_id>\d+)/delete_futureperson/$', faculty_views.delete_futureperson, name='delete_futureperson')
]
