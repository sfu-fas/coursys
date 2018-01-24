from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.http import urlquote, urlencode
from django.utils.safestring import mark_safe
from django.db.models import Q
from coredata.models import Role, CourseOffering, Member, Semester
from onlineforms.models import FormGroup, Form
from privacy.models import needs_privacy_signature, privacy_redirect
import urllib.request, urllib.parse, urllib.error
import datetime

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

# adapted from django_cas.decorators: returns 403 on failure, and passes **kwargs to test_func.
def user_passes_test(test_func, login_url=None,
                     redirect_field_name=REDIRECT_FIELD_NAME, force_privacy=False):
    """Replacement for django.contrib.auth.decorators.user_passes_test that
    returns 403 Forbidden if the user is already logged in.
    """

    if not login_url:
        login_url = settings.LOGIN_URL

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if test_func(request, **kwargs):
                if needs_privacy_signature(request, only_relevant_roles=not force_privacy):
                    # logic there: usually only check for the admin roles we know have a privacy implication. If we're
                    # passed force_privacy, then views must have the privacy agreement.
                    return privacy_redirect(request)
                else:
                    return view_func(request, *args, **kwargs)
            elif request.user.is_authenticated:
                return ForbiddenResponse(request)
            else:
                path = '%s?%s=%s' % (login_url, redirect_field_name,
                                     urlquote(request.get_full_path()))
                return HttpResponseRedirect(path)
        return wrapper
    return decorator


def HttpError(request, status=404, title="Not Found", error="The requested resource cannot be found.", errormsg=None, simple=False, exception=None):
    if simple:
        # this case is intended to produce human-readable HTML for API errors
        template = 'simple-error.html'
    else:
        template = 'error.html'
    resp = render(request, template, {'title': title, 'error': error, 'errormsg': errormsg})
    resp.status_code = status
    return resp

def ForbiddenResponse(request, errormsg=None, exception=None):
    error = mark_safe("You do not have permission to access this resource.")
    if not request.user.is_authenticated:
        login_url = settings.LOGIN_URL + '?' + urllib.parse.urlencode({'next': request.get_full_path()})
        error += mark_safe(' You are <strong>not logged in</strong>, so maybe <a href="%s">logging in</a> would help.' % (login_url))
    return HttpError(request, status=403, title="Forbidden", error=error, errormsg=errormsg)

def NotFoundResponse(request, errormsg=None, exception=None):
    return HttpError(request, status=404, title="Not Found", error="The requested resource cannot be found.", errormsg=errormsg)

def has_global_role(role, request, **kwargs):
    """
    Return True is the given user has the specified role
    """
    perms = Role.objects_fresh.filter(person__userid=request.user.username, role=role, unit__label="UNIV")
    count = perms.count()
    return count>0

def requires_role(role, get_only=None, login_url=None):
    """
    Allows access if user has the given role in ANY unit
    """
    def has_this_role(req, **kwargs):
        return has_role(role, req, get_only=get_only, **kwargs)
        
    actual_decorator = user_passes_test(has_this_role, login_url=login_url)
    return actual_decorator

def has_role(role, request, get_only=None, **kwargs):
    """
    Return True is the given user has the specified role in ANY unit
    """
    if isinstance(role, (list, tuple)):
        allowed = list(role)
    else:
        allowed = [role]
    if get_only and request.method == 'GET':
        if isinstance(get_only, (list, tuple)):
            allowed += list(get_only)
        else:
            allowed.append(get_only)

    roles = Role.objects_fresh.filter(person__userid=request.user.username, role__in=allowed).select_related('unit')
    request.units = set(r.unit for r in roles)
    count = roles.count()
    return count > 0

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
    TAs should only have access to courses they TAed up to a semester ago.
    """
    max_semester_name_for_tas = Semester.current().offset_name(-1)
    memberships = Member.objects.filter(Q(role__in=['INST', 'APPR']) | (Q(role='TA') &
                                                                        Q(offering__semester__name__gte=
                                                                        max_semester_name_for_tas)),
                                        offering__slug=course_slug,
                                        person__userid=request.user.username, offering__graded=True)\
        .exclude(offering__component="CAN")
    memberships = list(memberships)
    if memberships:
        request.member = memberships[0]
    return bool(memberships)

def requires_course_staff_by_slug(function=None, login_url=None):
    """
    Allows access if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_staff_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_course_instr_by_slug(request, course_slug, **kwargs):
    """
    Return True if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug' keyword.
    """
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username,
            role__in=['INST', 'APPR'], offering__graded=True).exclude(offering__component="CAN")
    count = memberships.count()
    return count>0

def requires_course_instr_by_slug(function=None, login_url=None):
    """
    Allows access if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug'.
    """
    actual_decorator = user_passes_test(is_course_instr_by_slug, login_url=login_url)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def is_form_admin_by_slug(request, form_slug, **kwargs):
    """
    Return True if user is a staff member (instructor, TA, approver) from course indicated by 'course_slug' keyword.
    """
    owner_ids = [f['owner'] for f in Form.objects.filter(slug=form_slug).values('owner')]
    groups = FormGroup.objects.filter(members__userid=request.user.username)
    request.formgroups = groups
    return groups.filter(id__in=owner_ids).count() > 0

def requires_form_admin_by_slug(function=None, login_url=None):
    """
    Allows access if user is an admin of the form indicated by the 'form_slug' keyword.
    """
    actual_decorator = user_passes_test(is_form_admin_by_slug, login_url=login_url, force_privacy=True)
    if function:
        return actual_decorator(function)
    else:
        return actual_decorator

def has_formgroup(request, **kwargs):
    """
    Return True is the given user is in any FormGroup
    """
    groups = FormGroup.objects.filter(members__userid=request.user.username)
    request.formgroups = groups
    return groups.count() > 0

def requires_formgroup(login_url=None):
    """
    Allows access if user has the given role in ANY FormGroup
    """
    actual_decorator = user_passes_test(has_formgroup, login_url=login_url, force_privacy=True)
    return actual_decorator


def is_discipline_user(request, course_slug, **kwargs):
    """
    Return True if user is a discipline user (instructor, approver or discipline admin)
    """
    # departmental discipline admins    
    roles = set()
    offerings = CourseOffering.objects.filter(slug=course_slug)
    if offerings:
        offering = offerings[0]
    else:
        return False

    perms = Role.objects_fresh.filter(person__userid=request.user.username, role='DISC', unit=offering.owner).count()
    perms += Role.objects_fresh.filter(person__userid=request.user.username, role='DISC', unit__label='UNIV').count()
    if perms>0:
        roles.add("DEPT")

    # instructors
    memberships = Member.objects.filter(offering__slug=course_slug, person__userid=request.user.username,
            role__in=['INST', 'APPR']).exclude(offering__component="CAN")
    count = memberships.count()
    
    if count>0:
        roles.add("INSTR")
    
    # record why we have permission in the session
    request.session['discipline-'+course_slug] = list(roles)
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
    roles = Role.objects.filter(person__userid=request.user.username, role__in=['FAC','SESS','COOP'])
    perms = roles.count()
    request.units = [r.unit for r in roles]
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


def service_unavailable(request, *args, **kwargs):
    # view called by featureflags when something is disabled
    return HttpError(request, status=503, title="Service Unavailable", error="This feature has been temporarily disabled due to server maintenance or load.", errormsg=None, simple=False)

def login_redirect(next_url):
    """
    Send the user to log in, and then to next_url
    """
    return HttpResponseRedirect(settings.LOGIN_URL + '?' + urlencode({'next': next_url}))


from coredata.models import Person
def get_person(user):
    '''
    Get the Person object associated with this user, or None.
    '''
    if not user.is_authenticated:
        return None

    if hasattr(user, 'person'):
        # Cache in the User object, since we might need it multiple times.
        pass
    else:
        try:
            user.person = Person.objects.get(userid=user.username)
        except Person.DoesNotExist:
            user.person = None

    return user.person
