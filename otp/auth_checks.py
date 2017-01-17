# Potentially application-specific logic for how we validate authentication and 2FA

from django.conf import settings
from django.utils import timezone
from courselib.auth import get_person

PASSWORD_AUTH_AGE = getattr(settings, 'PASSWORD_AUTH_AGE', 86400)
TWOFACTOR_AUTH_AGE = getattr(settings, 'TWOFACTOR_AUTH_AGE', 1209600)


def needs_2fa(request, user):
    '''
    Do we require 2FA for this user+request?

    Here: default is False, unless it's set for the user.
    '''
    person = get_person(user)
    return bool(person) and person.config.get('2fa', False)


def check_auth(session_info, request, user):
    '''
    Is the auth okay all-around? Returns a boolean pair: (Is password auth okay? Is 2FA okay?)
    '''
    now = timezone.now()

    good_auth = bool(session_info.last_auth) and (now - session_info.last_auth).total_seconds() < PASSWORD_AUTH_AGE

    good_2fa = (
        not needs_2fa(request, user) # 2FA is okay if we didn't need it anyway
        or (bool(session_info.last_2fa) and (now - session_info.last_2fa).total_seconds() < TWOFACTOR_AUTH_AGE)
    )

    return good_auth, good_2fa