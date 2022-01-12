from django.urls import re_path as url
from courselib.urlparts import USERID_SLUG, COMPONENT_SLUG, SUBMISSION_ID, GROUP_SLUG, SLUG_RE
import submission.views as submission_views

RESULT_SLUG = '(?P<result_slug>' + SLUG_RE + ')'

submission_patterns = [ # prefix /COURSE_SLUG/+ACTIVITY_SLUG/submission/
    url(r'^$', submission_views.show_components, name='show_components'),
    url(r'^history$', submission_views.show_components_submission_history, name='show_components_submission_history'),
    url(r'^download$', submission_views.download_activity_files, name='download_activity_files'),
    url(r'^components/new$', submission_views.add_component, name='add_component'),
    url(r'^components/edit$', submission_views.edit_single, name='edit_single'),
    url(r'^' + COMPONENT_SLUG + '/' + SUBMISSION_ID + '/get$', submission_views.download_file, name='download_file'),
    url(r'^' + USERID_SLUG + '/get$', submission_views.download_file, name='download_file'),
    url(r'^' + USERID_SLUG + '/view$', submission_views.show_student_submission_staff, name='show_student_submission_staff'),
    url(r'^' + USERID_SLUG + '/history$', submission_views.show_components_submission_history, name='show_components_submission_history'),
    url(r'^' + GROUP_SLUG + '/mark$', submission_views.take_ownership_and_mark, name='take_ownership_and_mark'),
    url(r'^' + USERID_SLUG + '/mark$', submission_views.take_ownership_and_mark, name='take_ownership_and_mark'),
]

similarity_patterns = [ # prefix /COURSE_SLUG/+ACTIVITY_SLUG/similarity/
    url(r'^$', submission_views.similarity, name='similarity'),
    url(r'^' + RESULT_SLUG + '/(?P<path>.*)$', submission_views.similarity_result, name='similarity_result'),
]