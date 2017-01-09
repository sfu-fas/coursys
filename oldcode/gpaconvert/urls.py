from django.conf.urls import patterns, url

gpaconvert_patterns = [
    # Admin Views
    url(r'^admin/$', gpaconvert_views.grade_sources, name='grade_sources', name = 'grade_source_index'),
    url(r'^admin/new-grade-source/$', gpaconvert_views.new_grade_source, name='new_grade_source', name='new_grade_source'),
    url(r'^admin/edit-grade-source/(?P<slug>.+)/$', gpaconvert_views.change_grade_source, name='change_grade_source', name='change_grade_source'),

    # User Views
    url(r'^$', gpaconvert_views.list_grade_sources, name='list_grade_sources', name = 'list_grade_sources_index'),
    url(r'^(?P<grade_source_slug>[\d\w-]+)$', gpaconvert_views.convert_grades, name='convert_grades'),
    url(r'^(?P<grade_source_slug>[\d\w-]+)/saved/(?P<slug>.+)/$', gpaconvert_views.view_saved, name='view_saved', name="view_saved_grades"),
]
