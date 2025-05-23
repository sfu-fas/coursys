from django.urls import re_path as url
from courselib.urlparts import USERID_OR_EMPLID, ACCOUNT_SLUG, PROJECT_SLUG, RA_SLUG, SLUG_RE, ID_RE
import ra.views as ra_views
from ra.views import RANewRequestWizard, RAEditRequestWizard, FORMS, check_gras, check_ra, check_nc

ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'
PROGRAM_SLUG = '(?P<program_slug>' + SLUG_RE + ')'
PROGRAM_ID = '(?P<program_id>' + ID_RE + ')'



ra_patterns = [ # prefix /ra/
    url(r'^download_current', ra_views.download, kwargs={'current': True}, name='download_current'),
    url(r'^download_all', ra_views.download, name='download_all'),
    url(r'^download_index', ra_views.download_index, name='download_index'),
    url(r'^download_admin', ra_views.download_admin, name='download_admin'),
    url(r'^new_request/', RANewRequestWizard.as_view(FORMS, 
                                                condition_dict={'graduate_research_assistant': check_gras, 
                                                'research_assistant': check_ra, 
                                                'non_continuing': check_nc}), 
                                                name='new_request'),
    url(r'^dashboard/' + RA_SLUG + '/edit_request$', RAEditRequestWizard.as_view(FORMS, 
                                                condition_dict={'graduate_research_assistant': check_gras, 
                                                'research_assistant': check_ra, 
                                                'non_continuing': check_nc}), 
                                                name='edit_request'),
    url(r'^dashboard/' + RA_SLUG + '/reappoint_request$', RANewRequestWizard.as_view(FORMS, 
                                                condition_dict={'graduate_research_assistant': check_gras, 
                                                'research_assistant': check_ra, 
                                                'non_continuing': check_nc}), 
                                                name='reappoint_request'),
    url(r'^dashboard/$', ra_views.dashboard, name='dashboard'),
    url(r'^active_appointments/$', ra_views.active_appointments, name='active_appointments'),
    url(r'^browse_appointments/$', ra_views.browse_appointments, name='browse_appointments'),
    url(r'^advanced_search/$', ra_views.advanced_search, name='advanced_search'),
    url(r'^advanced_search/appointee_appointments/' + USERID_OR_EMPLID + '/$', ra_views.appointee_appointments, name='appointee_appointments'),
    url(r'^advanced_search/supervisor_appointments/' + USERID_OR_EMPLID + '/$', ra_views.supervisor_appointments, name='supervisor_appointments'),
    url(r'^dashboard/' + RA_SLUG + '/view_request$', ra_views.view_request, name='view_request'),
    url(r'^dashboard/' + RA_SLUG + '/update_processor$', ra_views.update_processor, name='update_processor'),
    url(r'^dashboard/' + RA_SLUG + '/edit_request_notes$', ra_views.edit_request_notes, name='edit_request_notes'),
    url(r'^dashboard/' + RA_SLUG + '/delete_request$', ra_views.delete_request, name='delete_request'),
    url(r'^dashboard/' + RA_SLUG + '/delete_request_draft$', ra_views.delete_request_draft, name='delete_request_draft'),
    url(r'^dashboard/' + RA_SLUG + '/request_science_alive$', ra_views.request_science_alive, name='request_science_alive'),
    url(r'^dashboard/' + RA_SLUG + '/request_admin_update$', ra_views.request_admin_update, name='request_admin_update'),
    url(r'^dashboard/' + RA_SLUG + '/request_admin_paf_update$', ra_views.request_admin_paf_update, name='request_admin_paf_update'),
    url(r'^dashboard/' + RA_SLUG + '/request_paf$', ra_views.request_paf, name='request_paf'),
    url(r'^dashboard/' + RA_SLUG + '/request_offer_letter_update$', ra_views.request_offer_letter_update, name='request_offer_letter_update'),
    url(r'^dashboard/' + RA_SLUG + '/request_default_offer_letter$', ra_views.request_default_offer_letter, name='request_default_offer_letter'),
    url(r'^dashboard/' + RA_SLUG + '/request_offer_letter$', ra_views.request_offer_letter, name='request_offer_letter'),
    url(r'^dashboard/' + RA_SLUG + '/view_request_attachment_1$', ra_views.view_request_attachment_1, name='view_request_attachment_1'),
    url(r'^dashboard/' + RA_SLUG + '/view_request_attachment_2$', ra_views.view_request_attachment_2, name='view_request_attachment_2'),
    url(r'^dashboard/' + RA_SLUG + '/download_request_attachment_1$', ra_views.download_request_attachment_1, name='download_request_attachment_1'),
    url(r'^dashboard/' + RA_SLUG + '/download_request_attachment_2$', ra_views.download_request_attachment_2, name='download_request_attachment_2'),
    url(r'^' + RA_SLUG + '/admin_new_attach$', ra_views.new_admin_attachment, name='new_admin_attachment'),
    url(r'^' + RA_SLUG + '/admin_attach/' + ATTACH_SLUG + '/delete$', ra_views.delete_admin_attachment, name='delete_admin_attachment'),
    url(r'^' + RA_SLUG + '/admin_attach/' + ATTACH_SLUG + '/view', ra_views.view_admin_attachment, name='view_admin_attachment'),
    url(r'^' + RA_SLUG + '/admin_attach/' + ATTACH_SLUG + '/download$', ra_views.download_admin_attachment, name='download_admin_attachment'),
    
    # for tacontracts
    url(r'^accounts/new$', ra_views.new_account, name='new_account'),
    url(r'^accounts/$', ra_views.accounts_index, name='accounts_index'),
    url(r'^accounts/' + ACCOUNT_SLUG + '/delete$', ra_views.remove_account, name='remove_account'),
    url(r'^accounts/' + ACCOUNT_SLUG + '/edit$', ra_views.edit_account, name='edit_account'),

    # keeping these active, for now
    url(r'^browse', ra_views.browse, name='browse'),
    url(r'^download_historic', ra_views.download_ras, kwargs={'current': False}, name='download_historic'),
    url(r'^' + RA_SLUG + '/$', ra_views.view, name='view'),
    url(r'^' + RA_SLUG + '/form$', ra_views.form, name='form'),
    url(r'^' + RA_SLUG + '/letter$', ra_views.letter, name='letter'),
    url(r'^' + RA_SLUG + '/edit$', ra_views.edit, name='edit'),
    url(r'^' + RA_SLUG + '/edit_letter$', ra_views.edit_letter, name='edit_letter'),
    url(r'^' + RA_SLUG + '/delete$', ra_views.delete_ra, name='delete_ra'),
    url(r'^' + RA_SLUG + '/select_letter$', ra_views.select_letter, name='select_letter'),
    url(r'^' + RA_SLUG + r'/select_letter/(?P<print_only>[\w\-]+)' + '$', ra_views.select_letter, name='select_letter'),
    url(r'^' + RA_SLUG + '/new_attach$', ra_views.new_attachment, name='new_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/delete$', ra_views.delete_attachment, name='delete_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/view', ra_views.view_attachment, name='view_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/download$', ra_views.download_attachment, name='download_attachment'),
    url(r'^_personinfo$', ra_views.person_info, name='person_info'),
    url(r'^_personvisas$', ra_views.person_visas, name='person_visas'),
    url(r'^_payperiods$', ra_views.pay_periods, name='pay_periods'),

    # OLD RA
    #url(r'^download_current', ra_views.download_ras, name='download_current_ras'),
    #url(r'^$', ra_views.search, name='search'),
    #url(r'^search/' + USERID_OR_EMPLID + '/$', ra_views.student_appointments, name='student_appointments'),
    #url(r'^accounts/new$', ra_views.new_account, name='new_account'),
    #url(r'^accounts/$', ra_views.accounts_index, name='accounts_index'),
    #url(r'^accounts/' + ACCOUNT_SLUG + '/delete$', ra_views.remove_account, name='remove_account'),
    #url(r'^accounts/' + ACCOUNT_SLUG + '/edit$', ra_views.edit_account, name='edit_account'),
    #url(r'^projects/new$', ra_views.new_project, name='new_project'),
    #url(r'^projects/$', ra_views.projects_index, name='projects_index'),
    #url(r'^projects/' + PROJECT_SLUG + '/delete$', ra_views.remove_project, name='remove_project'),
    #url(r'^projects/' + PROJECT_SLUG + '/edit$', ra_views.edit_project, name='edit_project'),
    #url(r'^programs/new$', ra_views.new_program, name='new_program'),
    #url(r'^programs/$', ra_views.programs_index, name='programs_index'),
    #url(r'^programs/' + PROGRAM_ID + '/delete$', ra_views.delete_program, name='delete_program'),
    #url(r'^programs/' + PROGRAM_SLUG + '/edit$', ra_views.edit_program, name='edit_program'),
    #url(r'^semesters/$', ra_views.semester_config, name='semester_config'),
    #url(r'^semesters/(?P<semester_name>\d+)$', ra_views.semester_config, name='semester_config'),
    #url(r'^new$', ra_views.new, name='new'),
    #url(r'^found', ra_views.found, name='found'),
    #url(r'^' + RA_SLUG + '/reappoint$', ra_views.reappoint, name='reappoint'),
    #url(r'^new/' + USERID_OR_EMPLID + '/$', ra_views.new_student, name='new_student'),
]
