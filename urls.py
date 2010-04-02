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

    url(r'^log/$', 'log.views.index'),

    url(r'^$', 'courses.dashboard.views.index'),
    url(r'^' + '_all_news/$', 'dashboard.views.news_list'),

    url(r'^' + COURSE_SLUG + '/$', 'grades.views.course_info'),
    url(r'^' + COURSE_SLUG + '/_new_message$', 'dashboard.views.new_message'),

    url(r'^' + COURSE_SLUG + '/_groups$', 'groups.views.groupmanage'),
    url(r'^' + COURSE_SLUG + '/_groups/new$', 'groups.views.create'),
    url(r'^' + COURSE_SLUG + '/_groups/submit$', 'groups.views.submit'),
    url(r'^' + COURSE_SLUG + '/_groups/invite/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.invite'),
    url(r'^' + COURSE_SLUG + '/_groups/switchGroup/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.switch_group'),
    url(r'^' + COURSE_SLUG + '/_groups/delete/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.delete_group'),
    url(r'^' + COURSE_SLUG + '/_groups/changeName/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.change_name'),
    url(r'^' + COURSE_SLUG + '/_groups/join/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.join'),

    url(r'^' + COURSE_SLUG + '/_grades$', 'grades.views.all_grades'),
    url(r'^' + COURSE_SLUG + '/_new_numeric$', 'grades.views.add_numeric_activity'),
    url(r'^' + COURSE_SLUG + '/_new_letter$', 'grades.views.add_letter_activity'),
    url(r'^' + COURSE_SLUG + '/_new_cal_numeric$', 'grades.views.add_cal_numeric_activity'),
    url(r'^' + COURSE_SLUG + '/_formula_tester$', 'grades.views.formula_tester'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '$', 'grades.views.activity_info'),
    #url(r'^' + COURSE_ACTIVITY_SLUG + '/delete$', 'grades.views.delete_activity_review'),
    #url(r'^' + COURSE_ACTIVITY_SLUG + '/delete_confirm$', 'grades.views.delete_activity_confirm'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/edit$', 'grades.views.edit_activity'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/groups$', 'grades.views.activity_info_with_groups'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/students/' + USERID_SLUG + '$', 'grades.views.activity_info_student'),

    #url(r'^' + COURSE_SLUG + '/submission/$', 'submission.views.index'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/$', 'submission.views.show_components'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/new$', 'submission.views.add_submission'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/history$', 'submission.views.show_components_submission_history'),
    #url(r'^' + COURSE_SLUG + '/submission/' + ACTIVITY_SLUG + '/view/' + USERID_SLUG + '/history/$', 'submission.views.show_student_history_staff'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/components/new$', 'submission.views.add_component'),
    #url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/components/delete$', 'submission.views.confirm_remove'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/components/edit$', 'submission.views.edit_single'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + COMPONENT_SLUG + '/' + SUBMISSION_ID + '/get$', 'submission.views.download_file'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/get$', 'submission.views.download_file'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/view$', 'submission.views.show_student_submission_staff'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + GROUP_SLUG + '/mark$', 'submission.views.take_ownership_and_mark_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/mark$', 'submission.views.take_ownership_and_mark'),

    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/$', 'marking.views.manage_activity_components'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/positions/$', 'marking.views.manage_component_positions'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/common$', 'marking.views.manage_common_problems'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/new/students/' + USERID_SLUG + '/$', 'marking.views.marking_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/new/groups/' + GROUP_SLUG + '/$', 'marking.views.marking_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall$', 'marking.views.mark_all_students'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/students/' + USERID_SLUG + '/$', 'marking.views.mark_summary_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/groups/' + GROUP_SLUG + '/$', 'marking.views.mark_summary_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/students/' + USERID_SLUG + '/history', 'marking.views.mark_history_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/groups/' + GROUP_SLUG + '/history', 'marking.views.mark_history_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/attachments/' + '(?P<filepath>.*)$', 'marking.views.download_marking_attachment'),
    #url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')/mark_summary/(?P<filepath>.*)$', 'marking.views.download_marking_attachment'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/csv$', 'marking.views.export_csv'),
    url(r'^' + COURSE_SLUG + '/_copysetup/$', 'marking.views.copy_course_setup'),

    url(r'^roles/$', 'coredata.views.role_list'),
    url(r'^roles/new$', 'coredata.views.new_role'),
)
if settings.DEBUG:
    # URLs for development only:
    urlpatterns += patterns('',
        #(r'^admin/(.*)', admin.site.root),
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
        #(r'^import/', 'courses.coredata.views.importer'),
    )

