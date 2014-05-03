from django.conf.urls import url
from courselib.urlparts import UNIT_COURSE_SLUG, NOTE_ID, SEMESTER, COURSE_SLUG, ARTIFACT_SLUG, USERID_OR_EMPLID, NONSTUDENT_SLUG

privacy_patterns = [ # prefix /privacy/
    url(r'^$', 'privacy.views.privacy')
]
