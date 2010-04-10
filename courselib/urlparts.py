COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'
SLUG_RE = '[\w-]+'
ACTIVITY_SLUG_RE = SLUG_RE
GROUP_SLUG_RE =  'g-[\w-]+'

COURSE_SLUG = '(?P<course_slug>' + COURSE_SLUG_RE + ')'
ACTIVITY_SLUG = '(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')'

COURSE_ACTIVITY_SLUG = COURSE_SLUG + '/' + ACTIVITY_SLUG

USERID_SLUG = '(?P<userid>[\w\-]+)'
GROUP_SLUG  = '(?P<group_slug>' + GROUP_SLUG_RE + ')'

COMPONENT_SLUG = '(?P<component_slug>' + SLUG_RE + ')'

ID_RE = '\d+'
SUBMISSION_ID = '(?P<submission_id>' + ID_RE + ')'
ACTIVITY_MARK_ID = '(?P<mark_id>' + ID_RE + ')'

FILE_PATH='(?P<filepath>.*)'