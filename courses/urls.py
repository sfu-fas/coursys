from django.conf.urls import url, include
from django.conf import settings
from django.views.generic import TemplateView,  RedirectView

from courselib.urlparts import *
from dashboard.urls import config_patterns, news_patterns, calendar_patterns, docs_patterns
from coredata.urls import data_patterns, admin_patterns, sysadmin_patterns
from grades.urls import offering_patterns
from discipline.urls import discipline_patterns

handler404 = 'courselib.auth.NotFoundResponse'

urlpatterns = [
    url(r'^login/$', 'dashboard.views.login'),
    url(r'^logout/$', 'django_cas.views.logout', {'next_page': '/'}),
    url(r'^logout/(?P<next_page>.*)/$', 'django_cas.views.logout', name='auth_logout_next'),
    url(r'^robots.txt$', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),

    url(r'^$', 'dashboard.views.index'),
    url(r'^favicon.ico$', RedirectView.as_view(url=settings.STATIC_URL+'icons/favicon.ico', permanent=True)),
    url(r'^history$', 'dashboard.views.index_full'),

    url(r'^config/', include(config_patterns)),
    url(r'^news/', include(news_patterns)),
    url(r'^calendar/', include(calendar_patterns)),
    url(r'^docs/', include(docs_patterns)),
    url(r'^data/', include(data_patterns)),
    url(r'^admin/', include(admin_patterns)),
    url(r'^sysadmin/', include(sysadmin_patterns)),
    url(r'^discipline/', include(discipline_patterns)),

    url(r'^search$', 'dashboard.views.site_search'),

    url(r'^courses/(?P<tail>.*)$', RedirectView.as_view(url='/browse/%(tail)s', permanent=True)),
    url(r'^browse/$', 'coredata.views.browse_courses'),
    url(r'^browse/info/' + COURSE_SLUG + '$', 'coredata.views.browse_courses_info'),

    url(r'^students/$', 'dashboard.views.student_info'),
    url(r'^students/' + USERID_OR_EMPLID + '$', 'dashboard.views.student_info'),
    url(r'^photos/' + EMPLID_SLUG + '$', 'grades.views.student_photo'),
    url(r'^users/' + USERID_SLUG + '/$', RedirectView.as_view(url='/sysadmin/users/%(userid)s/', permanent=True)),  # accept the URL provided as get_absolute_url for user objects

    # course offering URL hierarchy
    url(r'^' + COURSE_SLUG + '/', include(offering_patterns)),


    # TA's TUGs

    #url(r'^' + COURSE_SLUG + '/config/tugs/$', 'ta.views.index_page'),
    url(r'^tugs/$', 'ta.views.all_tugs_admin'),
    url(r'^tugs/(?P<semester_name>\d+)$', 'ta.views.all_tugs_admin'),


    # TA postings/contracts

    url(r'^ta/$', 'ta.views.view_postings'),
    url(r'^ta/new_posting$', 'ta.views.edit_posting'),
    url(r'^ta/descriptions/$', 'ta.views.descriptions'),
    url(r'^ta/descriptions/new$', 'ta.views.new_description'),
    url(r'^ta/offers/$', 'ta.views.instr_offers'),
    url(r'^ta/' + POST_SLUG + '/$', 'ta.views.new_application'),
    url(r'^ta/' + POST_SLUG + '/_myinfo$', 'ta.views.get_info'),
    url(r'^ta/' + POST_SLUG + '/manual$', 'ta.views.new_application_manual'),
    url(r'^ta/' + POST_SLUG + '/offers$', 'ta.views.instr_offers'),
    url(r'^ta/' + POST_SLUG + '/admin$', 'ta.views.posting_admin'),
    url(r'^ta/' + POST_SLUG + '/applicant_csv$', 'ta.views.generate_csv'),
    url(r'^ta/' + POST_SLUG + '/applicant_csv_by_course$', 'ta.views.generate_csv_by_course'),
    url(r'^ta/' + POST_SLUG + '/edit$', 'ta.views.edit_posting'),
    url(r'^ta/' + POST_SLUG + '/bu$', 'ta.views.edit_bu'),
    url(r'^ta/' + POST_SLUG + '/bu_formset$', 'ta.views.bu_formset'),
    url(r'^ta/' + POST_SLUG + '/apps/$', 'ta.views.assign_tas'),
    url(r'^ta/' + POST_SLUG + '/' + COURSE_SLUG + '$', 'ta.views.assign_bus'),
    url(r'^ta/' + POST_SLUG + '/all_apps$', 'ta.views.view_all_applications'),
    url(r'^ta/' + POST_SLUG + '/print_all_applications$', 'ta.views.print_all_applications'),
    url(r'^ta/' + POST_SLUG + '/print_all_applications_by_course$', 'ta.views.print_all_applications_by_course'),
    url(r'^ta/' + POST_SLUG + '/late_apps$', 'ta.views.view_late_applications'),
    url(r'^ta/' + POST_SLUG + '/financial$', 'ta.views.view_financial'),
    url(r'^ta/' + POST_SLUG + '/contact', 'ta.views.contact_tas'),
    #url(r'^ta/contracts', 'ta.views.all_contracts'),
    url(r'^ta/' + POST_SLUG + '/contracts/$', 'ta.views.all_contracts'),
    url(r'^ta/' + POST_SLUG + '/contracts/csv$', 'ta.views.contracts_csv'),
    url(r'^ta/' + POST_SLUG + '/contracts/new$', 'ta.views.new_contract'),
    url(r'^ta/' + POST_SLUG + '/contracts/forms$', 'ta.views.contracts_forms'),
    url(r'^ta/' + POST_SLUG + '/contracts/' + USERID_SLUG + '/$', 'ta.views.view_contract'),
    url(r'^ta/' + POST_SLUG + '/contracts/' + USERID_SLUG + '/new$', 'ta.views.edit_contract'),
    url(r'^ta/' + POST_SLUG + '/contracts/' + USERID_SLUG + '/edit$', 'ta.views.edit_contract'),
    url(r'^ta/' + POST_SLUG + '/contracts/' + USERID_SLUG + '/form', 'ta.views.view_form'),
    url(r'^ta/' + POST_SLUG + '/contracts/' + USERID_SLUG + '/offer', 'ta.views.preview_offer'),
    url(r'^ta/' + POST_SLUG + '/contracts/' + USERID_SLUG + '/accept$', 'ta.views.accept_contract'),
    url(r'^ta/' + POST_SLUG + '/application/' + USERID_SLUG + '$', 'ta.views.view_application'),
    url(r'^ta/' + POST_SLUG + '/application/' + USERID_SLUG + '/update$', 'ta.views.update_application'),
    url(r'^ta/' + POST_SLUG + '/application/' + USERID_SLUG + '/edit', 'ta.views.edit_application'),



    #Graduate student database

    url(r'^grad/$', 'grad.views.index'),
    url(r'^my_grads/$', 'grad.views.supervisor_index'),
    #url(r'^grad/import$', 'grad.views.import_applic'),
    url(r'^grad/progress_reports', 'grad.views.progress_reports'),
    url(r'^grad/search$', 'grad.views.search'),
    url(r'^grad/search/save$', 'grad.views.save_search'),
    url(r'^grad/search/delete$', 'grad.views.delete_savedsearch'),
    url(r'^grad/qs', 'grad.views.quick_search'),
    #url(r'^grad/search_results$', 'grad.views.search_results'),

    url(r'^grad/program/new$', 'grad.views.new_program'),
    url(r'^grad/program/$', 'grad.views.programs'),
    url(r'^grad/requirement/$', 'grad.views.requirements'),
    url(r'^grad/requirement/new$', 'grad.views.new_requirement'),

    #url(r'^grad/letter/$', 'grad.views.letters'),
    url(r'^grad/letterTemplates/$', 'grad.views.letter_templates'),
    url(r'^grad/letterTemplates/new', 'grad.views.new_letter_template'),
    url(r'^grad/letterTemplates/' + LETTER_TEMPLATE_SLUG + '/manage', 'grad.views.manage_letter_template'),
    url(r'^grad/promises/$', 'grad.views.all_promises'),
    url(r'^grad/promises/(?P<semester_name>\d{4})$', 'grad.views.all_promises'),
    url(r'^grad/funding/$', 'grad.views.funding_report'),
    url(r'^grad/funding/(?P<semester_name>\d{4})$', 'grad.views.funding_report'),

    #url(r'^grad/' + GRAD_SLUG + '/old$', 'grad.views.view_all'),
    url(r'^grad/' + GRAD_SLUG + '/$', 'grad.views.view'),
    url(r'^grad/' + GRAD_SLUG + '/moreinfo$', 'grad.views.grad_more_info'),
    url(r'^grad/' + GRAD_SLUG + '/general$', 'grad.views.manage_general'),
    url(r'^grad/' + GRAD_SLUG + '/program', 'grad.views.manage_program'),
    url(r'^grad/' + GRAD_SLUG + '/start_end', 'grad.views.manage_start_end_semesters'),
    url(r'^grad/' + GRAD_SLUG + '/defence', 'grad.views.manage_defence'),
    url(r'^grad/' + GRAD_SLUG + '/form', 'grad.views.get_form'),
    url(r'^grad/' + GRAD_SLUG + '/supervisors$', 'grad.views.manage_supervisors'),
    url(r'^grad/' + GRAD_SLUG + '/supervisors/(?P<sup_id>\d+)/remove$', 'grad.views.remove_supervisor'),
    url(r'^grad/' + GRAD_SLUG + '/status$', 'grad.views.manage_status'),
    url(r'^grad/' + GRAD_SLUG + '/status/(?P<s_id>\d+)/remove$', 'grad.views.remove_status'),
    url(r'^grad/' + GRAD_SLUG + '/requirements$', 'grad.views.manage_requirements'),
    url(r'^grad/' + GRAD_SLUG + '/requirements/(?P<cr_id>\d+)/remove$', 'grad.views.remove_completedrequirement'),
    url(r'^grad/' + GRAD_SLUG + '/otherfunding$', 'grad.views.manage_otherfunding'),
    url(r'^grad/' + GRAD_SLUG + '/otherfunding/(?P<o_id>\d+)/remove$', 'grad.views.remove_otherfunding'),
    url(r'^grad/' + GRAD_SLUG + '/financial$', 'grad.views.financials'),
    url(r'^grad/' + GRAD_SLUG + '/financialcomments$', 'grad.views.manage_financialcomments'),
    url(r'^grad/' + GRAD_SLUG + '/financialcomments/(?P<f_id>\d+)/remove$', 'grad.views.remove_financialcomment'),
    url(r'^grad/' + GRAD_SLUG + '/promises$', 'grad.views.manage_promises'),
    url(r'^grad/' + GRAD_SLUG + '/promises/(?P<p_id>\d+)/remove$', 'grad.views.remove_promise'),
    #url(r'^grad/' + GRAD_SLUG + '/promises/new$', 'grad.views.new_promise'),
    url(r'^grad/' + GRAD_SLUG + '/scholarship$', 'grad.views.manage_scholarships'),
    url(r'^grad/' + GRAD_SLUG + '/scholarship/(?P<s_id>\d+)/remove$', 'grad.views.remove_scholarship'),
    url(r'^grad/' + GRAD_SLUG + '/letters$', 'grad.views.manage_letters'),
    url(r'^grad/' + GRAD_SLUG + '/letters/' + LETTER_TEMPLATE_SLUG + '/new$', 'grad.views.new_letter'),
    url(r'^grad/' + GRAD_SLUG + '/letters/_get_text/' + LETTER_TEMPLATE_ID + '$', 'grad.views.get_letter_text'),
    url(r'^grad/' + GRAD_SLUG + '/letters/' + LETTER_SLUG + '$', 'grad.views.get_letter'),
    url(r'^grad/' + GRAD_SLUG + '/letters/' + LETTER_SLUG + '/view$', 'grad.views.view_letter'),
    url(r'^grad/' + GRAD_SLUG + '/letters/' + LETTER_SLUG + '/copy', 'grad.views.copy_letter'),
    url(r'^grad/get_addresses$', 'grad.views.get_addresses'),
    url(r'^grad/scholarship_types$', 'grad.views.manage_scholarshipType'),
    url(r'^grad/financial_summary$', 'grad.views.student_financials'),
    #url(r'^grad/new', 'grad.views.new'),
    url(r'^grad/found', 'grad.views.not_found'),

    # RA database

    url(r'^ra/$', 'ra.views.search'),
    url(r'^ra/search/' + USERID_OR_EMPLID + '/$', 'ra.views.student_appointments'),
    url(r'^ra/new$', 'ra.views.new'),
    url(r'^ra/browse', 'ra.views.browse'),
    url(r'^ra/found', 'ra.views.found'),
    url(r'^ra/_payperiods$', 'ra.views.pay_periods'),
    url(r'^ra/_personinfo$', 'ra.views.person_info'),
    url(r'^ra/new/' + USERID_OR_EMPLID + '/$', 'ra.views.new_student'),
    url(r'^ra/accounts/new$', 'ra.views.new_account'),
    url(r'^ra/accounts/$', 'ra.views.accounts_index'),
    url(r'^ra/accounts/' + ACCOUNT_SLUG + '/delete$', 'ra.views.remove_account'),
    url(r'^ra/accounts/' + ACCOUNT_SLUG + '/edit$', 'ra.views.edit_account'),
    url(r'^ra/projects/new$', 'ra.views.new_project'),
    url(r'^ra/projects/$', 'ra.views.projects_index'),
    url(r'^ra/projects/' + PROJECT_SLUG + '/delete$', 'ra.views.remove_project'),
    url(r'^ra/projects/' + PROJECT_SLUG + '/edit$', 'ra.views.edit_project'),
    url(r'^ra/semesters/$', 'ra.views.semester_config'),
    url(r'^ra/semesters/(?P<semester_name>\d+)$', 'ra.views.semester_config'),
    url(r'^ra/' + RA_SLUG + '/$', 'ra.views.view'),
    url(r'^ra/' + RA_SLUG + '/form$', 'ra.views.form'),
    url(r'^ra/' + RA_SLUG + '/letter$', 'ra.views.letter'),
    url(r'^ra/' + RA_SLUG + '/edit$', 'ra.views.edit'),
    url(r'^ra/' + RA_SLUG + '/edit_letter$', 'ra.views.edit_letter'),
    url(r'^ra/' + RA_SLUG + '/reappoint$', 'ra.views.reappoint'),
    url(r'^ra/' + RA_SLUG + '/delete$', 'ra.views.delete_ra'),

    # Advisor Notes

    url(r'^advising/$', 'advisornotes.views.advising'),
    url(r'^advising/new_notes/$', 'advisornotes.views.rest_notes'),
    url(r'^advising/hide_note$', 'advisornotes.views.hide_note'),
    url(r'^advising/note_search$', 'advisornotes.views.note_search'),
    url(r'^advising/sims_search$', 'advisornotes.views.sims_search'),
    url(r'^advising/sims_add$', 'advisornotes.views.sims_add_person'),

    url(r'^advising/courses/$', 'advisornotes.views.view_courses'),
    url(r'^advising/courses/' + UNIT_COURSE_SLUG + '/new$', 'advisornotes.views.new_artifact_note'),
    url(r'^advising/courses/' + UNIT_COURSE_SLUG + '/moreinfo$', 'advisornotes.views.course_more_info'),
    url(r'^advising/courses/' + UNIT_COURSE_SLUG + '/' + NOTE_ID + '/edit$', 'advisornotes.views.edit_artifact_note'),
    url(r'^advising/courses/' + UNIT_COURSE_SLUG + '/$', 'advisornotes.views.view_course_notes'),
    url(r'^advising/offerings/$', 'advisornotes.views.view_course_offerings'),
    url(r'^advising/offerings/semesters$', 'advisornotes.views.view_all_semesters'),
    url(r'^advising/offerings/' + SEMESTER + '$', 'advisornotes.views.view_course_offerings'),
    url(r'^advising/offerings/' + COURSE_SLUG + '/new$', 'advisornotes.views.new_artifact_note'),
    url(r'^advising/offerings/' + COURSE_SLUG + '/$', 'advisornotes.views.view_offering_notes'),
    url(r'^advising/offerings/' + COURSE_SLUG + '/' + NOTE_ID + '/edit$', 'advisornotes.views.edit_artifact_note'),
    url(r'^advising/artifacts/$', 'advisornotes.views.view_artifacts'),
    url(r'^advising/artifacts/' + ARTIFACT_SLUG + '/new$', 'advisornotes.views.new_artifact_note'),
    url(r'^advising/artifacts/' + ARTIFACT_SLUG + '/$', 'advisornotes.views.view_artifact_notes'),
    url(r'^advising/artifacts/' + ARTIFACT_SLUG + '/' + NOTE_ID + '/edit$', 'advisornotes.views.edit_artifact_note'),
    url(r'^advising/new_artifact$', 'advisornotes.views.new_artifact'),
    url(r'^advising/artifacts/' + ARTIFACT_SLUG + '/edit$', 'advisornotes.views.edit_artifact'),
    url(r'^advising/artifacts/' + NOTE_ID + '/file', 'advisornotes.views.download_artifact_file'),

    url(r'^advising/students/' + USERID_OR_EMPLID + '/new$', 'advisornotes.views.new_note'),
    url(r'^advising/students/' + USERID_OR_EMPLID + '/$', 'advisornotes.views.student_notes'),
    url(r'^advising/students/' + NONSTUDENT_SLUG + '/$', 'advisornotes.views.student_notes'),
    url(r'^advising/students/' + NONSTUDENT_SLUG + '/merge$', 'advisornotes.views.merge_nonstudent'),
    url(r'^advising/students/' + USERID_OR_EMPLID + '/' + NOTE_ID + '/file', 'advisornotes.views.download_file'),
    url(r'^advising/students/' + USERID_OR_EMPLID + '/moreinfo$', 'advisornotes.views.student_more_info'),
    url(r'^advising/students/' + USERID_OR_EMPLID + '/courses$', 'advisornotes.views.student_courses'),
    url(r'^advising/students/' + USERID_OR_EMPLID + '/courses-data$', 'advisornotes.views.student_courses_data'),
    url(r'^advising/new_prospective_student', 'advisornotes.views.new_nonstudent'),
    #url(r'^advising/problems/$', 'advisornotes.views.view_problems'),
    #url(r'^advising/problems/resolved/$', 'advisornotes.views.view_resolved_problems'),
    #url(r'^advising/problems/(?P<prob_id>\d+)/$', 'advisornotes.views.edit_problem'),

    # Online Forms
    url(r'^forms/', include('onlineforms.urls')),

    # Online Forms
    url(r'^faculty/', include('faculty.urls')),

    # Alerts
    url(r'^alerts/', include('alerts.urls')),
    url(r'^reports/', include('reports.urls')),

    # GPA Calculator
    url(r'^gpacalc/', include('gpaconvert.urls')),

    # redirect old mobile URLs to rightful locations
    url(r'^m/(?P<urltail>.*)$',  RedirectView.as_view(url='/%(urltail)s/', permanent=True)),
]

if settings.DEPLOY_MODE != 'production':
    # URLs for development only:
    urlpatterns += [
        url(r'^fake_login', 'dashboard.views.fake_login'),
        url(r'^fake_logout', 'dashboard.views.fake_logout'),
    ]

