# Potentially application-specific logic for how we validate authentication and 2FA

from django.conf import settings
from django.utils import timezone
from courselib.auth import get_person
import datetime

PASSWORD_AUTH_AGE = getattr(settings, 'PASSWORD_AUTH_AGE', 86400)
TWOFACTOR_AUTH_AGE = getattr(settings, 'TWOFACTOR_AUTH_AGE', 1209600)
SESSION_EXPIRY_HOUR = getattr(settings, 'SESSION_EXPIRY_HOUR', 3)


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

    Only allows sessions to expire at 3am (actually, SESSION_EXPIRY_HOUR) to avoid interrupting workflow as much as possible.
    '''
    # when was the last moment we allowed sessions to time out? Use that as the effective "now" time.
    now = timezone.now()
    last_expiry =  datetime.datetime.combine(now.date(), datetime.time(hour=SESSION_EXPIRY_HOUR))
    if now.hour < SESSION_EXPIRY_HOUR:
        last_expiry -= datetime.timedelta(days=1)

    good_auth = bool(session_info.last_auth) and (last_expiry - session_info.last_auth).total_seconds() < PASSWORD_AUTH_AGE

    good_2fa = (
        not needs_2fa(request, user) # any 2FA is okay if we didn't need it
        or (bool(session_info.last_2fa) and (last_expiry - session_info.last_2fa).total_seconds() < TWOFACTOR_AUTH_AGE)
    )

    return good_auth, good_2fa