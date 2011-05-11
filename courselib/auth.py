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
            if test_func(request, **kwargs):
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


def ForbiddenResponse(request, errormsg=None):
    resp = render_to_response('403.html', {'errormsg': errormsg}, context_instance=RequestContext(request))
    resp.status_code = 403
    return resp

def NotFoundResponse(request):
    resp = render_to_response('404.html', context_instance=RequestContext(request))
    resp.status_code = 404
    return resp

def is_advisor(request, **kwargs):
    """
    Return True is the given user is an advisor
    """
    perms = Role.objects.filter(person__userid=request.user.username, role='ADVS')
    count = perms.count()
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

def has_global_role(role, request, **kwargs):
    """
    Return True is the given user has the specified role
    """
    perms = Role.objects.filter(person__userid=request.user.username, role=role, department="!!!!")
    count = perms.count()
    return count>0

def requires_role(role, login_url=None):
    """
    Allows access if user has the given role in ANY department
    """
    def has_this_role(req, **kwargs):
        return has_role(role, req, **kwargs)
        
    actual_decorator = user_passes_test(has_this_role, login_url=login_url)
    return actual_decorator

def has_role(role, request, **kwargs):
    """
    Return True is the given user has the specified role in ANY department
    """
    perms = Role.objects.filter(person__userid=request.user.username, role=role)
    count = perms.count()
    return count>0

def requires_global_role(role, login_url=None):
    """
    Allows access if user has the given role
    """
    def has_this_role(req, **kwargs):
        return has_global_role(role, req, **kwargs)
        
    actual_decorator = user_passes_test(has_this_role, login_url=login_url)
    return actual_decorator

def is_course_member_by_slug(request, course_slug, **kwargs):
    """
    Return True if user is any kind of member (non-dropped) from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.exclude(role="DROP", offering__component="CAN").filter(offering__slug=course_slug, person__userid=request.user.username, offering__graded=True)
    count = memberships.count()
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

def is_course_student_by_slug(request, course_slug, **kwargs):
    """
    Return True if user is student from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username, role="STUD", offering__graded=True).exclude(offering__component="CAN")
    count = memberships.count()
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

def is_course_staff_by_slug(request, course_slug, **kwargs):
    """
    Return True if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username,
            role__in=['INST', 'TA', 'APPR'], offering__graded=True).exclude(offering__component="CAN")
    count = memberships.count()
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


def is_discipline_user(request, course_slug, **kwargs):
    """
    Return True if user is a discipline user (instructor, approver or discipline admin)
    """
    # departmental discipline admins    
    # TODO: filter by offering.department once it's populated
    roles = set()
    offering = CourseOffering.objects.get(slug=course_slug)
    perms = Role.objects.filter(person__userid=request.user.username, role='DISC', department=offering.subject).count()
    if perms>0:
        roles.add("DEPT")

    # instructors
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username,
            role__in=['INST', 'APPR']).exclude(offering__component="CAN")
    count = memberships.count()
    
    if count>0:
        roles.add("INSTR")
    
    # record why we have permission in the session
    request.session['discipline-'+course_slug] = roles
    return bool(roles)


def requires_discipline_user(function=None, login_url=None):
    """
    Allows access if user is a discipline user for this case
    """
    actual_decorator = user_passes_test(is_discipline_user, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator


def is_instructor(request, **kwargs):
    """
    Return True if the user is an instructor
    """
    perms = Role.objects.filter(person__userid=request.user.username, role__in=['FAC','SESS','COOP']).count()
    return perms>0

def requires_instructor(function=None, login_url=None):
    """
    Allows access if user is an instructor.
    """
    actual_decorator = user_passes_test(is_instructor, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

