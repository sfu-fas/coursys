from django.urls import re_path as url
from courselib.urlparts import POST_SLUG, COURSE_SLUG, USERID_SLUG, ID_RE
import ta.views as ta_views


DESCRIPTION_ID = '(?P<description_id>' + ID_RE + ')'

ta_patterns = [ # prefix /ta/
    url(r'^$', ta_views.view_postings, name='view_postings'),
    url(r'^new_posting$', ta_views.edit_posting, name='edit_posting'),
    url(r'^descriptions/$', ta_views.descriptions, name='descriptions'),
    url(r'^descriptions/new$', ta_views.new_description, name='new_description'),
    url(r'^description/' + DESCRIPTION_ID + '/edit$', ta_views.edit_description, name='edit_description'),
    url(r'^description/' + DESCRIPTION_ID + '/delete$', ta_views.delete_description, name='delete_description'),
    url(r'^email_text$', ta_views.add_edit_ta_contract_email, name='edit_email'),
    url(r'^' + POST_SLUG + '/$', ta_views.new_application, name='new_application'),
    url(r'^' + POST_SLUG + '/_myinfo$', ta_views.get_info, name='get_info'),
    url(r'^' + POST_SLUG + '/manual$', ta_views.new_application_manual, name='new_application_manual'),
    url(r'^' + POST_SLUG + '/admin$', ta_views.posting_admin, name='posting_admin'),
    url(r'^' + POST_SLUG + '/applicant_csv$', ta_views.generate_csv, name='generate_csv'),
    url(r'^' + POST_SLUG + '/applicant_csv_by_course$', ta_views.generate_csv_by_course, name='generate_csv_by_course'),
    url(r'^' + POST_SLUG + '/edit$', ta_views.edit_posting, name='edit_posting'),
    url(r'^' + POST_SLUG + '/bu$', ta_views.edit_bu, name='edit_bu'),
    url(r'^' + POST_SLUG + '/bu_formset$', ta_views.bu_formset, name='bu_formset'),
    url(r'^' + POST_SLUG + '/apps/$', ta_views.assign_tas, name='assign_tas'),
    url(r'^' + POST_SLUG + '/apps/download$', ta_views.download_assign_csv, name='download_assign'),
    url(r'^' + POST_SLUG + '/' + COURSE_SLUG + '$', ta_views.assign_bus, name='assign_bus'),
    url(r'^' + POST_SLUG + '/all_apps$', ta_views.view_all_applications, name='view_all_applications'),
    url(r'^' + POST_SLUG + '/download_apps$', ta_views.download_all_applications, name='download_all_ta_applications'),
    url(r'^' + POST_SLUG + '/print_all_applications$', ta_views.print_all_applications, name='print_all_applications'),
    url(r'^' + POST_SLUG + '/print_all_applications_by_course$', ta_views.print_all_applications_by_course, name='print_all_applications_by_course'),
    url(r'^' + POST_SLUG + '/late_apps$', ta_views.view_late_applications, name='view_late_applications'),
    url(r'^' + POST_SLUG + '/financial$', ta_views.view_financial, name='view_financial'),
    url(r'^' + POST_SLUG + '/download_financial$', ta_views.download_financial, name='download_financial'),
    url(r'^' + POST_SLUG + '/contact', ta_views.contact_tas, name='contact_tas'),
    #url(r'^contracts', ta_views.all_contracts, name='all_contracts'),
    url(r'^' + POST_SLUG + '/contracts/$', ta_views.all_contracts, name='all_contracts'),
    url(r'^' + POST_SLUG + '/contracts/table_csv$', ta_views.contracts_table_csv, name='contracts_table_csv'),
    url(r'^' + POST_SLUG + '/contracts/csv$', ta_views.contracts_csv, name='contracts_csv'),
    url(r'^' + POST_SLUG + '/contracts/new$', ta_views.new_contract, name='new_contract'),
    url(r'^' + POST_SLUG + '/contracts/forms$', ta_views.contracts_forms, name='contracts_forms'),
    url(r'^' + POST_SLUG + '/contracts/' + USERID_SLUG + '/$', ta_views.view_contract, name='view_contract'),
    url(r'^' + POST_SLUG + '/contracts/' + USERID_SLUG + '/new$', ta_views.edit_contract, name='edit_contract'),
    url(r'^' + POST_SLUG + '/contracts/' + USERID_SLUG + '/edit$', ta_views.edit_contract, name='edit_contract'),
    url(r'^' + POST_SLUG + '/contracts/' + USERID_SLUG + '/form', ta_views.view_form, name='view_form'),
    url(r'^' + POST_SLUG + '/contracts/' + USERID_SLUG + '/offer', ta_views.preview_offer, name='preview_offer'),
    url(r'^' + POST_SLUG + '/contracts/' + USERID_SLUG + '/accept$', ta_views.accept_contract, name='accept_contract'),
    url(r'^' + POST_SLUG + '/application/' + USERID_SLUG + '$', ta_views.view_application, name='view_application'),
    url(r'^' + POST_SLUG + '/application/' + USERID_SLUG + '/download_resume/$', ta_views.download_resume,
        name="download_resume"),
    url(r'^' + POST_SLUG + '/application/' + USERID_SLUG + '/view_resume/$', ta_views.view_resume, name="view_resume"),
    url(r'^' + POST_SLUG + '/application/' + USERID_SLUG + '/download_transcript/$', ta_views.download_transcript,
        name="download_transcript"),
    url(r'^' + POST_SLUG + '/application/' + USERID_SLUG + '/view_transcript/$', ta_views.view_transcript,
        name="view_transcript"),
    url(r'^' + POST_SLUG + '/application/' + USERID_SLUG + '/update$', ta_views.update_application, name='update_application'),
    url(r'^' + POST_SLUG + '/application/' + USERID_SLUG + '/edit', ta_views.edit_application, name='edit_application'),
    url(r'^ta-exclude-choice$', ta_views.ta_exclude_choice, name='ta-exclude-choice'),   
]

tug_patterns = [ # prefix /tugs/
    url(r'^$', ta_views.all_tugs_admin, name='all_tugs_admin'),
    url(r'^(?P<semester_name>\d+)$', ta_views.all_tugs_admin, name='all_tugs_admin'),
]
