from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'gpaconvert.views.list_grade_sources'),
)
