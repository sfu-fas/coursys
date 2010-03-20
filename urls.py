from django.conf.urls.defaults import *
from django.conf import settings

if settings.DEBUG:
    from django.contrib import admin
    admin.autodiscover()

from courselib.urlparts import *

handler404 = 'courselib.auth.NotFoundResponse'

urlpatterns = patterns('',
    url(r'^login/$', 'django_cas.views.login'),
    url(r'^logout/$', 'django_cas.views.logout'),

    url(r'^$', 'courses.dashboard.views.index'),
    url(r'^' + COURSE_SLUG + '/$', 'grades.views.course_info'),
    
    url(r'^' + COURSE_SLUG + '/groups$', 'groups.views.groupmanage'),
    url(r'^' + COURSE_SLUG + '/groups/new$', 'groups.views.create'),
    url(r'^' + COURSE_SLUG + '/groups/submit$', 'groups.views.submit'),
    url(r'^' + COURSE_SLUG + '/groups/invite/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.invite'),
    url(r'^' + COURSE_SLUG + '/groups/join/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.join'),

    url(r'^' + COURSE_SLUG + '/new_numeric$', 'grades.views.add_numeric_activity'),
    url(r'^' + COURSE_SLUG + '/new_letter$', 'grades.views.add_letter_activity'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/delete$', 'grades.views.delete_activity_review'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/delete_confirm$', 'grades.views.delete_activity_confirm'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/edit$', 'grades.views.edit_activity'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '$', 'grades.views.activity_info'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/students/' + USERID_SLUG + '$', 'grades.views.activity_info_student'),
    
    #url(r'^' + COURSE_SLUG + '/submission/$', 'submission.views.index'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/$', 'submission.views.show_components'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/new$', 'submission.views.add_submission'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/history$', 'submission.views.show_components_submission_history'),
    #url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/view/' + USERID_SLUG + '/history/$', 'submission.views.show_student_history_staff'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/components/new$', 'submission.views.add_component'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/components/delete$', 'submission.views.confirm_remove'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/components/edit$', 'submission.views.edit_single'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/get$', 'submission.views.download_file'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/view$', 'submission.views.show_student_submission_staff'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/mark$', 'submission.views.take_ownership_and_mark'),

    #url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/$', 'marking.views.list_activities'),        
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/$', 'marking.views.manage_activity_components'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/common$', 'marking.views.manage_common_problems'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/new/student/' + USERID_SLUG + '/$', 'marking.views.marking_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/new/group/' + GROUP_SLUG + '/$', 'marking.views.marking_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall$', 'marking.views.mark_all_students'),            
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/students/' + USERID_SLUG + '/$', 'marking.views.mark_summary'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/students/' + USERID_SLUG + '/history', 'marking.views.mark_history'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/attachments/' + '(?P<filepath>.*)$', 'marking.views.download_marking_attachment'),

    #url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')/mark_summary/(?P<filepath>.*)$', 'marking.views.download_marking_attachment'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/csv$', 'marking.views.export_csv'),
    
    
    url(r'^roles/$', 'courses.coredata.views.role_list'),
    url(r'^roles/new$', 'courses.coredata.views.new_role'),
    
    # for Advisor_A
    #(r'^advisors_A/', include('advisors_A.urls')),
    #for Advisors_B
    #(r'^advisors_B/', include('advisors_B.urls')),
    
    # for Marking
    #(r'^marking/', include('marking.urls')),

    # for Grades
    (r'^grades/', include('grades.urls')),

    # for groups
    #(r'^groups/', include('groups.urls')),

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

