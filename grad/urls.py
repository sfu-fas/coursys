from django.urls import re_path as url
from courselib.urlparts import LETTER_TEMPLATE_SLUG, GRAD_SLUG, LETTER_TEMPLATE_ID, LETTER_SLUG, ID_RE
import grad.views as grad_views

ST_ID = '(?P<st_id>' + ID_RE + ')'

grad_patterns = [ # prefix /grad/
    url(r'^$', grad_views.index, name='index'),
    #url(r'^import$', grad_views.import_applic, name='import_applic'),
    url(r'^config$', grad_views.config, name='config'),
    url(r'^reports$', grad_views.reports, name='reports'),
    url(r'^progress_reports', grad_views.progress_reports, name='progress_reports'),
    url(r'^search$', grad_views.search, name='search'),
    url(r'^search_index$', grad_views.search_index, name='search_index'),
    url(r'^search/save$', grad_views.save_search, name='save_search'),
    url(r'^search/delete$', grad_views.delete_savedsearch, name='delete_savedsearch'),
    url(r'^qs', grad_views.quick_search, name='quick_search'),

    url(r'^program/new$', grad_views.new_program, name='new_program'),
    url(r'^program/(?P<program_id>\d+)/edit', grad_views.edit_program, name='edit_program'),
    url(r'^program/$', grad_views.programs, name='programs'),
    url(r'^requirement/$', grad_views.requirements, name='requirements'),
    url(r'^requirement/new$', grad_views.new_requirement, name='new_requirement'),
    url(r'^requirement/(?P<requirement_id>\d+)/toggle$', grad_views.toggle_requirement, name='toggle_requirement'),

    url(r'^letterTemplates/$', grad_views.letter_templates, name='letter_templates'),
    url(r'^letterTemplates/new', grad_views.new_letter_template, name='new_letter_template'),
    url(r'^letterTemplates/' + LETTER_TEMPLATE_SLUG + '/manage', grad_views.manage_letter_template, name='manage_letter_template'),
    url(r'^promises/$', grad_views.all_promises, name='all_promises'),
    url(r'^promises/(?P<semester_name>\d{4})$', grad_views.all_promises, name='all_promises'),
    url(r'^promises_csv/(?P<semester_name>\d{4})$', grad_views.download_promises, name='download_promises'),
    url(r'^funding/$', grad_views.funding_report, name='funding_report'),
    url(r'^funding/(?P<semester_name>\d{4})$', grad_views.funding_report, name='funding_report'),
    url(r'^funding/(?P<semester_name>\d{4})/download_tas', grad_views.funding_report_download, kwargs={'type': 'tas'}, name='funding_report_tas'),
    url(r'^funding/(?P<semester_name>\d{4})/download_ras', grad_views.funding_report_download, kwargs={'type': 'ras'}, name='funding_report_ras'),
    url(r'^funding/(?P<semester_name>\d{4})/download_scholarships', grad_views.funding_report_download, kwargs={'type': 'scholarships'}, name='funding_report_scholarships'),
    url(r'^funding/(?P<semester_name>\d{4})/download_other', grad_views.funding_report_download, kwargs={'type': 'other'}, name='funding_report_other'),
    url(r'^financials_report', grad_views.financials_report, name='financials_report'),
    
    url(r'^' + GRAD_SLUG + '/$', grad_views.view, name='view'),
    url(r'^' + GRAD_SLUG + '/update_note$', grad_views.update_note, name='update_note'),
    url(r'^' + GRAD_SLUG + '/moreinfo$', grad_views.grad_more_info, name='grad_more_info'),
    url(r'^' + GRAD_SLUG + '/general$', grad_views.manage_general, name='manage_general'),
    url(r'^' + GRAD_SLUG + '/program', grad_views.manage_program, name='manage_program'),
    url(r'^' + GRAD_SLUG + '/start_end', grad_views.manage_start_end_semesters, name='manage_start_end_semesters'),
    url(r'^' + GRAD_SLUG + '/defence', grad_views.manage_defence, name='manage_defence'),
    url(r'^' + GRAD_SLUG + '/form', grad_views.get_form, name='get_form'),
    url(r'^' + GRAD_SLUG + '/supervisors$', grad_views.manage_supervisors, name='manage_supervisors'),
    url(r'^' + GRAD_SLUG + '/supervisors/(?P<sup_id>\d+)/remove$', grad_views.remove_supervisor, name='remove_supervisor'),
    url(r'^' + GRAD_SLUG + '/status$', grad_views.manage_status, name='manage_status'),
    url(r'^' + GRAD_SLUG + '/status/(?P<s_id>\d+)/remove$', grad_views.remove_status, name='remove_status'),
    url(r'^' + GRAD_SLUG + '/requirements$', grad_views.manage_requirements, name='manage_requirements'),
    url(r'^' + GRAD_SLUG + '/requirements/(?P<cr_id>\d+)/remove$', grad_views.remove_completedrequirement, name='remove_completedrequirement'),
    url(r'^' + GRAD_SLUG + '/otherfunding$', grad_views.manage_otherfunding, name='manage_otherfunding'),
    url(r'^' + GRAD_SLUG + '/otherfunding/(?P<o_id>\d+)/remove$', grad_views.remove_otherfunding, name='remove_otherfunding'),
    url(r'^' + GRAD_SLUG + '/financial$', grad_views.financials, name='financials'),
    url(r'^' + GRAD_SLUG + '/financial-(?P<style>\w+)$', grad_views.financials, name='financials'),
    url(r'^' + GRAD_SLUG + '/financialcomments$', grad_views.manage_financialcomments, name='manage_financialcomments'),
    url(r'^' + GRAD_SLUG + '/financialcomments/(?P<f_id>\d+)/remove$', grad_views.remove_financialcomment, name='remove_financialcomment'),
    url(r'^' + GRAD_SLUG + '/promises$', grad_views.manage_promises, name='manage_promises'),
    url(r'^' + GRAD_SLUG + '/promises/(?P<p_id>\d+)/remove$', grad_views.remove_promise, name='remove_promise'),
    url(r'^' + GRAD_SLUG + '/progress_reports$', grad_views.manage_progress, name='manage_progress'),
    url(r'^' + GRAD_SLUG + '/progress_reports/(?P<p_id>\d+)/remove$', grad_views.remove_progress, name='remove_progress'),
    url(r'^' + GRAD_SLUG + '/documents$', grad_views.manage_documents, name='manage_documents'),
    url(r'^' + GRAD_SLUG + '/documents/(?P<d_id>\d+)/remove$', grad_views.remove_document, name='remove_document'),
    url(r'^' + GRAD_SLUG + '/documents/(?P<d_id>\d+)/download$', grad_views.download_file, name='download_file'),
    url(r'^' + GRAD_SLUG + '/scholarship$', grad_views.manage_scholarships, name='manage_scholarships'),
    url(r'^' + GRAD_SLUG + '/scholarship/(?P<s_id>\d+)/remove$', grad_views.remove_scholarship, name='remove_scholarship'),
    url(r'^' + GRAD_SLUG + '/letters$', grad_views.manage_letters, name='manage_letters'),
    url(r'^' + GRAD_SLUG + '/letters/' + LETTER_TEMPLATE_SLUG + '/new$', grad_views.new_letter, name='new_letter'),
    url(r'^' + GRAD_SLUG + '/letters/_get_text/' + LETTER_TEMPLATE_ID + '$', grad_views.get_letter_text, name='get_letter_text'),
    url(r'^' + GRAD_SLUG + '/letters/' + LETTER_SLUG + '$', grad_views.get_letter, name='get_letter'),
    url(r'^' + GRAD_SLUG + '/letters/' + LETTER_SLUG + '/view$', grad_views.view_letter, name='view_letter'),
    url(r'^' + GRAD_SLUG + '/letters/' + LETTER_SLUG + '/copy', grad_views.copy_letter, name='copy_letter'),
    url(r'^' + GRAD_SLUG + '/letters/' + LETTER_SLUG + '/delete$', grad_views.remove_letter, name='remove_letter'),
    url(r'^' + GRAD_SLUG + '/letters/' + LETTER_SLUG + '/send_email$', grad_views.send_letter_email, name='send_letter_email'),
    url(r'^get_addresses$', grad_views.get_addresses, name='get_addresses'),
    url(r'^scholarship_types$', grad_views.manage_scholarshiptypes, name='manage_scholarshiptypes'),
    url(r'^scholarship_types/new$', grad_views.new_scholarshiptype, name='new_scholarshiptype'),
    url(r'^scholarship_types/' + ST_ID + '/edit$', grad_views.edit_scholarshiptype, name='edit_scholarshiptype'),
    url(r'^scholarship_types/' + ST_ID + '/toggle$', grad_views.toggle_scholarshiptype, name='toggle_scholarshiptype'),
    url(r'^financial_summary$', grad_views.student_financials, name='student_financials'),
    #url(r'^new', grad_views.new, name='new'),
    url(r'^found', grad_views.not_found, name='not_found'),
]
