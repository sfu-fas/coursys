The goals here:

1. Password authentication is valid for settings.OTP_AUTH_AGE seconds.
2. Two-factor authentication is valid for settings.OTP_2FA_AGE seconds.
3. These are potentially independent (but must be less than or equal to) session cookie age, which is part of Django's
   session middleware and controlled by settings.SESSION_COOKIE_AGE.

This lets us application demand password authentication more often than the second factor.

Parts of the workflow:
- The Authentication2FAMiddleware middleware augments Django's AuthenticationMiddleware which must be added before it.
  The Authentication2FAMiddleware will check the ages of the standard password authentication and the 2FA. If either are
  missing or out-of-date, it will set request.user to an AnonymousUser, thus making @login_required and friends think
  the user isn't logged in.
- The metadata about the session needed to make this work is stored by models.SessionInfo objects.
- The views.login_2fa view replaces the standard Django login view (settings.PASSWORD_LOGIN_URL). If the
  AuthenticationMiddleware or Authentication2FAMiddleware decides the user isn't (fully) logged in, this view handles
  the decision of further redirecting to standard Django login (settings.PASSWORD_LOGIN_URL), or showing them the 2FA
  auth page.
- The django-otp app is used for the core logic of the 2FA. The middleware calls it to check the OTP status, and the
  login view calls to verify and record the 2FA status. http://pythonhosted.org/django-otp/
- The actual "who is really authenticated?" logic is in auth_checks.py. As it's written, the user must password
  authenticate every 24 hours, but 2FA lasts two weeks.


TODO:
- Need frontend to send a recovery code to the user's recovery email (Person.config['recovery_email']).
- Need frontend that allows a user to enable 2FA for their account (Person.config['2fa'] = True).
- Need frontend to set up recovery codes (with django-otp StaticDevice). (They are be accepted if in the DB.)