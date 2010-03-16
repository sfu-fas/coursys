from django.db.models import Count
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.http import urlquote

from coredata.models import Role, CourseOffering, Member

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

# adapted from django_cas.decorators: uses 403.html template, and passes **kwargs to test_func.
def user_passes_test(test_func, login_url=None,
                     redirect_field_name=REDIRECT_FIELD_NAME):
    """Replacement for django.contrib.auth.decorators.user_passes_test that
    returns 403 Forbidden if the user is already logged in.
    """

    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if test_func(request.user, **kwargs):
                return view_func(request, *args, **kwargs)
            elif request.user.is_authenticated():
                resp = render_to_response('403.html', context_instance=RequestContext(request))
                resp.status_code = 403
                return resp
            else:
                path = '%s?%s=%s' % (login_url, redirect_field_name,
                                     urlquote(request.get_full_path()))
                return HttpResponseRedirect(path)
        return wrapper
    return decorator


def is_advisor(u, **kwargs):
    """
    Return True is the given user is an advisor
    """
    perms = Role.objects.filter(person__userid=u.username, role='ADVS')
    count = perms.aggregate(Count('person'))['person__count']
    return count>0

def requires_advisor(function=None, login_url=None):
    """
    Allows access if user is an advisor.
    """
    actual_decorator = user_passes_test(is_advisor, login_url=login_url)
    if function:
        return  actual_decorator(function)
    else:
        return actual_decorator

def has_role(role, u, **kwargs):
    """
    Return True is the given user has the specified role
    """
    perms = Role.objects.filter(person__userid=u.username, role=role)
    count = perms.aggregate(Count('person'))['person__count']
    return count>0

def requires_role(role, login_url=None):
    """
    Allows access if user has the given role
    """
    def has_this_role(u, **kwargs):
        return has_role(role, u, **kwargs)
        
    actual_decorator = user_passes_test(has_this_role, login_url=login_url)
    #print has_this_role
    return actual_decorator

def is_course_member_by_slug(u, course_slug, **kwargs):
    """
    Return True if user is any kind of member (non-dropped) from course indicated by 'course_slug' keyword.
    """
    #offering = get_object_or_404(CourseOffering, slug=course_slug)
    memberships = Member.objects.exclude(role="DROP").filter(offering__slug=course_slug, person__userid=u.username)
    count = memberships.aggregate(Count('person'))['person__count']
    return count>0

def requires_course_by_slug(function=None, login_url=None):
    """
    Allows access if user is any kind of member (non-dropped) from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_member_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_course_student_by_slug(u, course_slug, **kwargs):
    """
    Return True if user is student from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=u.username, role="STUD")
    count = memberships.aggregate(Count('person'))['person__count']
    return count>0

def requires_course_student_by_slug(function=None, login_url=None):
    """
    Allows access if user is student from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_student_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_course_staff_by_slug(u, course_slug, **kwargs):
    """
    Return True if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug' keyword.
    """
    #offering = get_object_or_404(CourseOffering, slug=course_slug)
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=u.username,
            role__in=['INST', 'TA', 'APPR'])
    count = memberships.aggregate(Count('person'))['person__count']
    return count>0

def requires_course_staff_by_slug(function=None, login_url=None):
    """
    Allows access if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_staff_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator


def is_faculty_member(u, **kwargs):
    """
    Return True if the user is a faculty member
    """
    perms = Role.objects.filter(person__userid=u.username, role='FAC')
    count = perms.aggregate(Count('person'))['person__count']
    return count>0

def requires_faculty_member(function=None, login_url=None):
    """
    Allows access if user is a faculty member.
    """
    #print function
    #print login_url
    actual_decorator = user_passes_test(is_faculty_member, login_url=login_url)
    if function:
        return  actual_decorator(function)
    else:
        return actual_decorator

