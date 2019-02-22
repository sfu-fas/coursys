from django.conf.urls import url
from courselib.urlparts import COURSE_SLUG, PAGE_LABEL
import pages.views as pages_views

pages_patterns = [ # prefix /COURSE_SLUG/pages/
    url(r'^$', pages_views.index_page, name='index_page'),
    url(r'^_all$', pages_views.all_pages, name='all_pages'),
    url(r'^_new$', pages_views.new_page, name='new_page'),
    url(r'^_newfile$', pages_views.new_file, name='new_file'),
    url(r'^_push$', pages_views.api_import, name='api_import'),
    url(r'^' + PAGE_LABEL + '$', pages_views.view_page, name='view_page'),
    url(r'^' + PAGE_LABEL + '/view$', pages_views.view_file, name='view_file'),
    url(r'^' + PAGE_LABEL + '/download$', pages_views.download_file, name='download_file'),
    url(r'^' + PAGE_LABEL + '/edit$', pages_views.edit_page, name='edit_page'),
    url(r'^' + PAGE_LABEL + '/history$', pages_views.page_history, name='page_history'),
    url(r'^' + PAGE_LABEL + '/version/(?P<version_id>\d+)$', pages_views.page_version, name='page_version'),
]
