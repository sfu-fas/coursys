from django.conf.urls import url
from courselib.urlparts import USERID_SLUG, COMPONENT_SLUG, SUBMISSION_ID, GROUP_SLUG

submission_patterns = [ # prefix /COURSE_SLUG/+ACTIVITY_SLUG/submission/
    url(r'^$', 'submission.views.show_components'),
    url(r'^history$', 'submission.views.show_components_submission_history'),
    url(r'^download$', 'submission.views.download_activity_files'),
    url(r'^components/new$', 'submission.views.add_component'),
    url(r'^components/edit$', 'submission.views.edit_single'),
    url(r'^' + COMPONENT_SLUG + '/' + SUBMISSION_ID + '/get$', 'submission.views.download_file'),
    url(r'^' + USERID_SLUG + '/get$', 'submission.views.download_file'),
    url(r'^' + USERID_SLUG + '/view$', 'submission.views.show_student_submission_staff'),
    url(r'^' + USERID_SLUG + '/history$', 'submission.views.show_components_submission_history'),
    url(r'^' + GROUP_SLUG + '/mark$', 'submission.views.take_ownership_and_mark'),
    url(r'^' + USERID_SLUG + '/mark$', 'submission.views.take_ownership_and_mark'),
]