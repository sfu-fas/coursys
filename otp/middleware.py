"""
The goals here:

1. Password authentication is valid for settings.OTP_AUTH_AGE seconds.
2. Two-factor authentication is valid for settings.OTP_2FA_AGE seconds.
3. These are potentially independent (but must be less than or equal to) session cookie age, which is part of Django's
   session middleware and controlled by settings.SESSION_COOKIE_AGE.

This lets us application demand password authentication more often than the second factor.
"""

from django.contrib.auth.models import AnonymousUser
from django_otp.middleware import OTPMiddleware

from .models import SessionInfo, needs_2fa


def auth_okay(request, user):
    '''
    Look at the SessionInfo corresponding to this user's session: does it meet the OTP auth criteria?
    '''
    session_info = SessionInfo.for_request(request, user=user) # side effect: sets request.session_info.
    if session_info is None:
        return False, False
    else:
        good_auth, good_2fa = session_info.okay_auth(request, user)
        return good_auth and good_2fa


class Authentication2FAMiddleware(OTPMiddleware):
    def process_request(self, request):
        assert hasattr(request, 'user'), (
            "'django.contrib.auth.middleware.AuthenticationMiddleware' must be before Authentication2FAMiddleware."
        )

        # By the time we get here, Django's AuthenticationMiddleware has checked the standard authentication:
        # password-authenticated session is good for request.user (or it's an AnonymousUser).

        # All we can do here is tighten the restrictions (unless we set request.user to a real User instance, which
        # we don't).

        password_user = request.user # the user who was password-authenticated by Django
        request.maybe_stale_user = password_user
        request.session_info = SessionInfo.for_request(request, user=password_user)

        if not password_user.is_authenticated():
            # No user authenticated in any way: we have nothing more to check.
            return

        # Do the django_otp verification checks, so we know that there's a 2fa on the session.
        self._verify_user(request, password_user)
        if needs_2fa(request, password_user) and not password_user.is_verified():
            # User has password-authenticated, but 2FA is required and we don't have it.
            request.user = AnonymousUser()
            return

        if not auth_okay(request, password_user):
            # User has password-authenticated and 2FA, but they're out of date by our standards.
            request.user = AnonymousUser()
            return