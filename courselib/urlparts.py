COURSE_SLUG_RE = '(?:\d{4}|\d{4}[a-z]{2})-[a-z]{2,4}-\w{3,4}-[a-z0-9]{2,4}'
SLUG_RE = '[\w\-\.]+'
ACTIVITY_SLUG_RE = SLUG_RE
GROUP_SLUG_RE = 'g-[\w\-\.]*'

COURSE_SLUG = '(?P<course_slug>' + COURSE_SLUG_RE + ')'
ACTIVITY_SLUG = '(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')'

COURSE_ACTIVITY_SLUG = COURSE_SLUG + '/\+' + ACTIVITY_SLUG
COURSE_ACTIVITY_SLUG_OLD = COURSE_SLUG + '/' + ACTIVITY_SLUG

USERID_SLUG = '(?P<userid>[\w\-]+)'
# USERID_OR_EMPLID is the same as USERID_SLUG, but might be a userid or emplid (use
# in cases where there might be no active computing account for the person).
USERID_OR_EMPLID = USERID_SLUG
EMPLID_SLUG = '(?P<emplid>[\d]+)'
GROUP_SLUG = '(?P<group_slug>' + GROUP_SLUG_RE + ')'

COMPONENT_SLUG = '(?P<component_slug>' + SLUG_RE + ')'

ID_RE = '\d+'
SUBMISSION_ID = '(?P<submission_id>' + ID_RE + ')'
ACTIVITY_MARK_ID = '(?P<mark_id>' + ID_RE + ')'

FILE_PATH = '(?P<filepath>.*)'
CASE_SLUG = '(?P<case_slug>[\w\-]+)'
DGROUP_SLUG = '(?P<group_slug>[\w\-]+)'

SEMESTER = '(?P<semester>\d{4})'
PAGE_LABEL = '(?P<page_label>[\w\-_\.]+)'

NONSTUDENT_SLUG = '(?P<nonstudent_slug>' + SLUG_RE + ')'
NOTE_ID = '(?P<note_id>' + ID_RE + ')'
UNIT_COURSE_SLUG = '(?P<unit_course_slug>' + SLUG_RE + ')'
ARTIFACT_SLUG = '(?P<artifact_slug>' + SLUG_RE + ')'

APP_ID = '(?P<app_id>' + ID_RE + ')'
UNIT_SLUG = '(?P<unit_slug>' + SLUG_RE + ')'
GRAD_SLUG = '(?P<grad_slug>' + SLUG_RE + ')'
POST_SLUG = '(?P<post_slug>' + SLUG_RE + ')'
RA_SLUG = '(?P<ra_slug>' + SLUG_RE + ')'
ACCOUNT_SLUG = '(?P<account_slug>' + SLUG_RE + ')'
PROJECT_SLUG = '(?P<project_slug>' + SLUG_RE + ')'

LETTER_SLUG = '(?P<letter_slug>' + SLUG_RE + ')'
LETTER_TEMPLATE_SLUG = '(?P<letter_template_slug>' + SLUG_RE + ')'
LETTER_TEMPLATE_ID = '(?P<letter_template_id>' + ID_RE + ')'
