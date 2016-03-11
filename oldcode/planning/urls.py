from django.conf.urls.defaults import patterns, url
from courselib.urlparts import SEMESTER, USERID_SLUG, COURSE_SLUG, SLUG_RE

PLAN_SLUG = '(?P<plan_slug>[\w\-]+)'
PLANNED_OFFERING_SLUG = '(?P<planned_offering_slug>[\w\-]+)'

urlpatterns = patterns('',
    url(r'^teaching/$', 'planning.views.instructor_index'),
    url(r'^teaching/courses$', 'planning.views.edit_capability'),
    url(r'^teaching/courses/(?P<course_id>\w+)/delete$', 'planning.views.delete_capability'),

    url(r'^teaching/semesters$', 'planning.views.edit_intention'),
    url(r'^teaching/semester/' + SEMESTER + '/delete$', 'planning.views.delete_intention'),
    url(r'^teaching/credits/$', 'planning.views.view_teaching_credits_inst'),
    url(r'^teaching/equivalent/(?P<equivalent_id>\d+)/$', 'planning.views.view_teaching_equivalent_inst'),
    url(r'^teaching/equivalent/(?P<equivalent_id>\d+)/edit/$', 'planning.views.edit_teaching_equivalent_inst'),
    url(r'^teaching/equivalent/(?P<equivalent_id>\d+)/remove/$', 'planning.views.remove_teaching_equiv_inst'),
    url(r'^teaching/equivalent/new/$', 'planning.views.new_teaching_equivalent_inst'),
    url(r'^teaching/admin/$', 'planning.views.view_insts_in_unit'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/$', 'planning.views.view_teaching_credits_admin'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/new-equivalent/$', 'planning.views.new_teaching_equivalent_admin'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/equivalent/(?P<equivalent_id>\d+)/$', 'planning.views.view_teaching_equivalent_admin'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/equivalent/(?P<equivalent_id>\d+)/edit/$', 'planning.views.edit_teaching_equivalent_admin'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/equivalent/(?P<equivalent_id>\d+)/confirm/$', 'planning.views.confirm_teaching_equivalent'),
    url(r'^teaching/admin/instructor/' + USERID_SLUG + '/course/' + COURSE_SLUG + '/edit/$', 'planning.views.edit_course_offering_credits'),

    url(r'^planning/teaching_plans$', 'planning.views.view_intentions'),
    url(r'^planning/teaching_plans/add$', 'planning.views.planner_create_intention'),
    url(r'^planning/teaching_plans/' + SEMESTER + '/$', 'planning.views.view_semester_intentions'),
    url(r'^planning/teaching_plans/' + SEMESTER + '/add$', 'planning.views.planner_create_intention'),
    url(r'^planning/teaching_plans/' + SEMESTER + '/' + USERID_SLUG + '/edit$', 'planning.views.planner_edit_intention'),
    url(r'^planning/teaching_plans/' + SEMESTER + '/' + USERID_SLUG + '/delete$', 'planning.views.planner_delete_intention'),

    url(r'^planning/teaching_capabilities$', 'planning.views.view_capabilities'),
    url(r'^planning/teaching_capabilities/' + USERID_SLUG + '/edit$', 'planning.views.planner_edit_capabilities'),
    url(r'^planning/teaching_capabilities/' + USERID_SLUG + '/(?P<course_id>\w+)/delete$', 'planning.views.planner_delete_capability'),

    url(r'^planning/$', 'planning.views.admin_index'),
    url(r'^planning/add_plan$', 'planning.views.create_plan'),
    url(r'^planning/copy_plan$', 'planning.views.copy_plan'),
    url(r'^planning/courses$', 'planning.views.manage_courses'),
    url(r'^planning/courses/add$', 'planning.views.create_course'),
    url(r'^planning/courses/(?P<course_slug>' + SLUG_RE + ')/edit$', 'planning.views.edit_course'),
    url(r'^planning/courses/(?P<course_id>' + SLUG_RE + ')/delete$', 'planning.views.delete_course'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/edit$', 'planning.views.edit_plan'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '$', 'planning.views.update_plan'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/' + PLANNED_OFFERING_SLUG + '/delete$', 'planning.views.delete_planned_offering'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/' + PLANNED_OFFERING_SLUG + '/edit$', 'planning.views.edit_planned_offering'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/' + PLANNED_OFFERING_SLUG + '/assign$', 'planning.views.view_instructors'),
    url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/delete$', 'planning.views.delete_plan'),

    url(r'^semester_plans/$', 'planning.views.plans_index'),
    url(r'^semester_plans/' + SEMESTER + '/' + PLAN_SLUG + '$', 'planning.views.view_plan'),
)
