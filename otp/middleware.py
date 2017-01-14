"""
The goals here:

1. Password authentication is valid for settings.OTP_AUTH_AGE seconds.
2. Two-factor authentication is valid for settings.OTP_2FA_AGE seconds.
3. These are potentially independent (but must be less than or equal to) session cookie age, which is part of Django's
   session middleware and controlled by settings.SESSION_COOKIE_AGE.

This lets us application demand password authentication more (or possibly less) often than the second factor.
"""


from django.conf import settings
from django.contrib import auth
from django.contrib.auth import load_backend
from django.contrib.auth.backends import RemoteUserBackend
from django.core.exceptions import ImproperlyConfigured
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject

from django.utils.crypto import constant_time_compare
from django.contrib.auth import _get_user_session_key, BACKEND_SESSION_KEY, HASH_SESSION_KEY

from .models import SessionInfo

OTP_AUTH_AGE = getattr(settings, 'OTP_AUTH_AGE', 10000)
OTP_2FA_AGE = getattr(settings, 'OTP_2FA_AGE', 100000)

def get_user(request):
    """
    Clone of django.contrib.auth.middleware.AuthenticationMiddleware (from Django 1.10), but honours the settings.OTP_AUTH_AGE limit.
    """
    from django.contrib.auth.models import AnonymousUser
    user = None

    session_info = SessionInfo.for_request(request)
    if session_info is None:
        return AnonymousUser()

    print session_info.__dict__

    #if session_info.age_auth() > OTP_AUTH_AGE or session_info.age_2fa() > OTP_2FA_AGE:
        # either the standard-auth or 2fa is out of date: authentication isn't valid anymore.
    #    return AnonymousUser()

    try:
        user_id = _get_user_session_key(request)
        backend_path = request.session[BACKEND_SESSION_KEY]
    except KeyError:
        pass
    else:
        if backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            user = backend.get_user(user_id)
            # Verify the session
            if hasattr(user, 'get_session_auth_hash'):
                session_hash = request.session.get(HASH_SESSION_KEY)
                session_hash_verified = session_hash and constant_time_compare(
                    session_hash,
                    user.get_session_auth_hash()
                )
                if not session_hash_verified:
                    request.session.flush()
                    user = None

    return user or AnonymousUser()


class TimeLimitedAuthenticationMiddleware(MiddlewareMixin):
    """
    Clone of django.contrib.auth.middleware.AuthenticationMiddleware (from Django 1.10), but honours the settings.OTP_AUTH_AGE limit.
    """
    def process_request(self, request):
        assert hasattr(request, 'session'), (
            "The Django authentication middleware requires session middleware "
            "to be installed. Edit your MIDDLEWARE%s setting to insert "
            "'django.contrib.sessions.middleware.SessionMiddleware' before "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'."
        ) % ("_CLASSES" if settings.MIDDLEWARE is None else "")
        request.user = SimpleLazyObject(lambda: get_user(request))