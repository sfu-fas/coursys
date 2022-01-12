from django.urls import re_path as url

from courselib.urlparts import USERID_OR_EMPLID
from . import views


quiz_patterns = [
    url(r'^$', views.index, name='index'),
    url(r'^edit$', views.EditView.as_view(), name='edit'),
    url(r'^edit/(?P<question_id>\d+)$', views.question_add_version, name='question_add_version'),
    url(r'^edit/(?P<question_id>\d+)-(?P<version_id>\d+)$', views.question_edit, name='question_edit'),
    url(r'^order/(?P<question_id>\d+)$', views.question_reorder, name='question_reorder'),
    url(r'^delete/(?P<question_id>\d+)$', views.question_delete, name='question_delete'),
    url(r'^delete/(?P<question_id>\d+)-(?P<version_id>\d+)$', views.version_delete, name='version_delete'),
    url(r'^add$', views.question_add, name='question_add'),
    url(r'^preview$', views.preview_student, name='preview_student'),
    url(r'^export$', views.export, name='export'),
    url(r'^import$', views.import_, name='import'),
    url(r'^notable-history$', views.strange_history, name='strange_history'),
    url(r'^photo-compare$', views.photo_compare, name='photo_compare'),
    url(r'^instructions$', views.instructions, name='instructions'),
    url(r'^submissions/$', views.submissions, name='submissions'),
    url(r'^submissions/' + USERID_OR_EMPLID + '$', views.view_submission, name='view_submission'),
    url(r'^submissions/' + USERID_OR_EMPLID + r'/history$', views.submission_history, name='submission_history'),
    url(r'^submissions/' + USERID_OR_EMPLID + r'/file/(?P<answer_id>\d+)/(?P<secret>\w+)$', views.submitted_file, name='submitted_file'),
    url(r'^submissions/' + USERID_OR_EMPLID + r'/photo/(?P<submission_id>\d+)', views.submission_photo, name='submission_photo'),
    url(r'^download$', views.download_submissions, name='download_submissions'),
    url(r'^csv$', views.download_submissions_csv, name='download_submissions_csv'),
    url(r'^special/$', views.special_cases, name='special_cases'),
    url(r'^special/add$', views.special_case_add, name='special_case_add'),
    url(r'^special/delete/(?P<sc_id>\d+)$', views.special_case_delete, name='special_case_delete'),
    url(r'^mark-setup$', views.marking_setup, name='marking_setup'),
    url(r'^mark/$', views.marking, name='marking'),
    url(r'^mark-next/$', views.mark_next, name='mark_next'),
    url(r'^mark-next/(?P<question_id>\d+)$', views.mark_next, name='mark_next_question'),
    url(r'^mark-next/(?P<question_id>\d+)-(?P<version_id>\d+)$', views.mark_next, name='mark_next_version'),
    url(r'^mark/(?P<member_id>\d+)$', views.mark_student, name='mark_student'),
]