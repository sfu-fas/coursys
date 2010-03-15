COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'
SLUG_RE = '[\w-]+'
ACTIVITY_SLUG_RE = SLUG_RE
COURSE_SLUG = '(?P<course_slug>' + COURSE_SLUG_RE + ')'
ACTIVITY_SLUG = '(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')'

COURSE_ACTIVITY_SLUG = COURSE_SLUG + '/' + ACTIVITY_SLUG

USERID_SLUG = '(?P<userid>\w+)'
