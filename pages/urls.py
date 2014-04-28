from django.conf.urls import url
from courselib.urlparts import COURSE_SLUG, PAGE_LABEL

pages_patterns = [ # prefix /COURSE_SLUG/pages/
    url(r'^$', 'pages.views.index_page'),
    url(r'^_all$', 'pages.views.all_pages'),
    url(r'^_new$', 'pages.views.new_page'),
    url(r'^_import$', 'pages.views.import_site'),
    url(r'^_newfile$', 'pages.views.new_file'),
    url(r'^_convert$', 'pages.views.convert_content'),
    url(r'^_push$', 'pages.views.api_import'),
    url(r'^' + PAGE_LABEL + '$', 'pages.views.view_page'),
    url(r'^' + PAGE_LABEL + '/view$', 'pages.views.view_file'),
    url(r'^' + PAGE_LABEL + '/download$', 'pages.views.download_file'),
    url(r'^' + PAGE_LABEL + '/edit$', 'pages.views.edit_page'),
    url(r'^' + PAGE_LABEL + '/import$', 'pages.views.import_page'),
    url(r'^' + PAGE_LABEL + '/history$', 'pages.views.page_history'),
    url(r'^' + PAGE_LABEL + '/version/(?P<version_id>\d+)$', 'pages.views.page_version'),
    url(r'^' + PAGE_LABEL + '/_convert$', 'pages.views.convert_content'),
]
