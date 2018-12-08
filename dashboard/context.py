from django.conf import settings
from coredata.models import Member
from cache_utils.decorators import cached
from courselib.branding import product_name, help_email


@cached(3600)
def is_instr_ta(userid):
    if not userid:
        return False
    members = Member.objects.filter(role__in=['INST', 'TA'])
    return members.exists()

@cached(3600)
def is_student(userid):
    if not userid:
        return False
    members = Member.objects.filter(role__in=['STUD'])
    return members.exists()

def media(request):
    """
    Add context things that we need
    """
    # A/B testing: half of instructors and TAs see a different search box
    instr_ta = is_instr_ta(request.user.username)
    instr_ta_ab = instr_ta and request.user.is_authenticated and request.user.id % 2 == 0
    stud = is_student(request.user.username)
    # GRAD_DATE(TIME?)_FORMAT for the grad/ra/ta apps
    return {'GRAD_DATE_FORMAT': settings.GRAD_DATE_FORMAT,
            'GRAD_DATETIME_FORMAT': settings.GRAD_DATETIME_FORMAT,
            'LOGOUT_URL': settings.LOGOUT_URL,
            'LOGIN_URL': settings.LOGIN_URL,
            'STATIC_URL': settings.STATIC_URL,
            'is_instr_ta': instr_ta,
            'instr_ta_ab': instr_ta_ab,
            'stud' : stud,
            'request_path': request.path,
            'CourSys': product_name(request),
            'help_email': help_email(request),
            }
