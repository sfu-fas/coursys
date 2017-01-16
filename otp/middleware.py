"""
The goals here:

1. Password authentication is valid for settings.OTP_AUTH_AGE seconds.
2. Two-factor authentication is valid for settings.OTP_2FA_AGE seconds.
3. These are potentially independent (but must be less than or equal to) session cookie age, which is part of Django's
   session middleware and controlled by settings.SESSION_COOKIE_AGE.

This lets us application demand password authentication more often than the second factor.
"""

from django_otp.middleware import OTPMiddleware

from .models import SessionInfo


def auth_ages_okay(request, user):
    '''
    Look at the SessionInfo corresponding to this user's session: does it meet the OTP auth criteria?
    '''
    session_info = SessionInfo.for_request(request, user=user) # side effect: sets request.session_info.

    return (
        session_info is not None # we can check the session metadata to verify something,
        and session_info.okay_age_auth(user) # and standard auth is up to date,
        and session_info.okay_age_2fa(user) # and 2FA is up to date.
    )


class Authentication2FAMiddleware(OTPMiddleware):
    def process_request(self, request):
        from django.contrib.auth.models import AnonymousUser
        assert hasattr(request, 'user'), (
            "'django.contrib.auth.middleware.AuthenticationMiddleware' must be before Authentication2FAMiddleware."
        )

        # By the time we get here, Django's AuthenticationMiddleware has checked the standard authentication:
        # password-authenticated session is good for request.user (or it's an AnonymousUser).

        password_user = request.user
        request.maybe_stale_user = password_user
        request.session_info = SessionInfo.for_request(request, user=password_user)

        if not password_user.is_authenticated():
            # No user authenticated in any way: we're done.
            return

        # Do the django_otp verification checks, so we know if there's a 2fa on the session.
        self._verify_user(request, password_user)
        if not password_user.is_verified():
            # User has password-authenticated, but no 2FA. That doesn't count.
            # TODO: what if this user doesn't need 2FA?
            request.user = AnonymousUser()
            return

        if not auth_ages_okay(request, password_user):
            # User has password-authenticated and 2FA, but they're out of date by our standards.
            request.user = AnonymousUser()
            return