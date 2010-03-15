from django.conf.urls.defaults import *
from django.conf import settings

if settings.DEBUG:
    from django.contrib import admin
    admin.autodiscover()

from courselib.urlparts import *

urlpatterns = patterns('',
    url(r'^login/$', 'django_cas.views.login'),
    url(r'^logout/$', 'django_cas.views.logout'),

    url(r'^$', 'courses.dashboard.views.index'),
    url(r'^' + COURSE_SLUG + '/$', 'grades.views.course_info'),
    
    url(r'^' + COURSE_SLUG + '/activities/new_numeric$', 'grades.views.add_numeric_activity'),
    url(r'^' + COURSE_SLUG + '/activities/new_letter$', 'grades.views.add_letter_activity'),
    url(r'^' + COURSE_SLUG + '/activities/' + ACTIVITY_SLUG + '/delete$', 'grades.views.delete_activity_review'),
    url(r'^' + COURSE_SLUG + '/activities/' + ACTIVITY_SLUG + '/delete_confirm$', 'grades.views.delete_activity_confirm'),
    url(r'^' + COURSE_SLUG + '/activities/' + ACTIVITY_SLUG + '/edit$', 'grades.views.edit_activity'),
    url(r'^' + COURSE_SLUG + '/activities/' + ACTIVITY_SLUG + '$', 'grades.views.activity_info'),

    url(r'^' + COURSE_SLUG + '/groups$', 'groups.views.groupmanage'),
    url(r'^' + COURSE_SLUG + '/groups/new$', 'groups.views.create'),
    url(r'^' + COURSE_SLUG + '/groups/submit$', 'groups.views.submit'),
    url(r'^' + COURSE_SLUG + '/groups/join/(?P<group_slug>' + SLUG_RE + ')/$', 'groups.views.join'),

    
    url(r'^' + COURSE_SLUG + '/submission/$', 'submission.views.index'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/$', 'submission.views.show_components'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/view/' + USERID_SLUG + '/$', 'submission.views.show_student_submission_staff'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/history/$', 'submission.views.show_components_submission_history'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/view/' + USERID_SLUG + '/history/$', 'submission.views.show_student_history_staff'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/submit/$', 'submission.views.add_submission'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/add_component/$', 'submission.views.add_component'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/remove/$', 'submission.views.confirm_remove'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/edit/$', 'submission.views.edit_single'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/download/$', 'submission.views.download_file'),
    url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/mark/' + USERID_SLUG + '/$', 'submission.views.take_ownership_and_mark'),
    
    
    url(r'^roles/$', 'courses.coredata.views.role_list'),
    url(r'^roles/new$', 'courses.coredata.views.new_role'),
    
    # for Advisor_A
    #(r'^advisors_A/', include('advisors_A.urls')),
    #for Advisors_B
    #(r'^advisors_B/', include('advisors_B.urls')),
    
    # for Marking
    (r'^marking/', include('marking.urls')),

    # for Grades
    (r'^grades/', include('grades.urls')),

    # for groups
    (r'^groups/', include('groups.urls')),

    #submission
    #(r'^submission/', include('submission.urls')),
)
if settings.DEBUG:
    # URLs for development only:
    urlpatterns += patterns('',
        (r'^admin/(.*)', admin.site.root),
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
        #(r'^import/', 'courses.coredata.views.importer'),
    )

