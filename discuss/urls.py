from django.urls import re_path as url
from courselib.urlparts import SLUG_RE
import discuss.views as discuss_views

discussion_patterns = [ # prefix /COURSE_SLUG/discussion/
    url(r'^$', discuss_views.discussion_index, name='discussion_index'),
    url(r'^create_topic/$', discuss_views.create_topic, name='create_topic'),
    url(r'^subscribe$', discuss_views.manage_discussion_subscription, name='manage_discussion_subscription'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/$', discuss_views.view_topic, name='view_topic'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/edit$', discuss_views.edit_topic, name='edit_topic'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/change$', discuss_views.change_topic_status, name='change_topic_status'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/remove/(?P<message_slug>' + SLUG_RE + ')$', discuss_views.remove_message, name='remove_message'),
    url(r'^topic/(?P<topic_slug>' + SLUG_RE + ')/edit/(?P<message_slug>' + SLUG_RE + ')$', discuss_views.edit_message, name='edit_message'),
    url(r'^download_json$', discuss_views.download, name='download'),
]
