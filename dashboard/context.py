from django.conf import settings
from coredata.models import Member
from cache_utils.decorators import cached

@cached(60)
def context_memberships(userid):
    if userid:
        return Member.get_memberships(userid)[0]
    else:
        return []

def media(request):
    """
    Add context things that we need
    """
    # GRAD_DATE(TIME?)_FORMAT for the grad/ra/ta apps
    return {'GRAD_DATE_FORMAT': settings.GRAD_DATE_FORMAT,
            'GRAD_DATETIME_FORMAT': settings.GRAD_DATETIME_FORMAT,
            'LOGOUT_URL': settings.LOGOUT_URL,
            'LOGIN_URL': settings.LOGIN_URL,
            'memberships': context_memberships(request.user.username),
            'request_path': request.path,
            }