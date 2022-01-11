
from . import auth_checks
from django.db import models
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.signals import user_logged_in, user_logged_out

from django.db.models.signals import post_save
from django.utils import timezone

from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice
from django.conf import settings

from six.moves.urllib.parse import quote, urlencode
import base64

ALL_DEVICE_CLASSES = [TOTPDevice, StaticDevice]

# This could be configurable from settings. It isn't at the moment.

check_auth = auth_checks.check_auth
needs_2fa = auth_checks.needs_2fa


def all_otp_devices(user, confirmed=True):
    for Dev in ALL_DEVICE_CLASSES:
        devs = Dev.objects.devices_for_user(user, confirmed=confirmed)
        for d in devs: # could be a python3 'yield from'
            yield d


def totpauth_url(totp_dev):
    # https://github.com/google/google-authenticator/wiki/Key-Uri-Format
    label = totp_dev.user.username.encode('utf8')

    # We need two separate issuers, otherwise deploying in prod will override our authenticator token from
    # dev
    if settings.DEPLOY_MODE == 'production':
        issuer = b'CourSys'
    else:
        issuer = b'CourSys-DEV'

    query = [
        ('secret', base64.b32encode(totp_dev.bin_key)),
        ('digits', totp_dev.digits),
        ('issuer', issuer)
    ]
    return b'otpauth://totp/%s?%s' % (label, urlencode(query).encode('ascii'))


# based on http://stackoverflow.com/a/4631504/1236542
class SessionInfo(models.Model):
    '''
    Meta-information about Sessions, so we can record when authentications happened.
    '''
    session = models.OneToOneField(Session, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    last_auth = models.DateTimeField(null=True)
    last_2fa = models.DateTimeField(null=True)

    @classmethod
    def for_session(cls, session, save_new=True):
        'Retrieve or create a SessionInfo for this Session.'
        assert isinstance(session, Session)
        try:
            si = cls.objects.get(session=session)
        except (SessionInfo.DoesNotExist):
            si = SessionInfo(session=session)
            if save_new:
                si.save()

        return si

    @classmethod
    def for_sessionstore(cls, sessionstore, save_new=True):
        'Retrieve or create a SessionInfo for this SessionStore.'
        assert isinstance(sessionstore, SessionStore)
        try:
            si = cls.objects.get(session__session_key=sessionstore.session_key)
        except (SessionInfo.DoesNotExist):
            si = SessionInfo(session=Session.objects.get(session_key=sessionstore.session_key))
            if save_new:
                si.save()

        return si

    @classmethod
    def for_request(cls, request, save_new=True, user=None):
        'Retrieve the SessionInfo for this request, if it has an active session.'
        if hasattr(request, 'session_info') and request.session_info is not None:
            # already have it.
            return request.session_info

        if request.session.session_key is None:
            # no session: no point in looking.
            request.session_info = None
        else:
            try:
                si = cls.for_sessionstore(request.session, save_new=save_new)
            except (Session.DoesNotExist):
                request.session_info = None
                return

            request.session_info = si

        return request.session_info

    @classmethod
    def just_logged_in(cls, request):
        'Records that the session associated with this request just logged in (by django auth).'
        si = cls.for_request(request, save_new=False)
        if si is None:
            return
        si.last_auth = timezone.now()
        si.save()
        return si

    @classmethod
    def just_logged_out(cls, request):
        'Records that the session associated with this request just logged out.'
        si = cls.for_request(request, save_new=False)
        if si is None:
            return
        si.last_auth = None
        si.save()
        return si

    @classmethod
    def just_2fa(cls, request):
        'Records that the session associated with this request just completed 2FA.'
        si = cls.for_request(request, save_new=False)
        si.last_2fa = timezone.now()
        si.save()
        return si

    def __str__(self):
        return '%s@%s' % (self.session_id, self.created)

    def okay_auth(self, request, user):
        '''
        Is the auth okay for this request/user?

        Hook here to allow apps to customize behaviour. Returns a boolean pair:
            Is standard Django auth okay?
            Is 2FA okay?
        May assume that Django auth *and* OTP auth have said yes. Only need to restrict further.
        '''
        return check_auth(self, request, user)


def logged_in_listener(request, **kwargs):
    SessionInfo.just_logged_in(request)

def logged_out_listener(request, **kwargs):
    SessionInfo.just_logged_out(request)

user_logged_in.connect(logged_in_listener)
user_logged_out.connect(logged_out_listener)

def session_create_listener(instance, **kwargs):
    instance.session_info = SessionInfo.for_session(instance)

post_save.connect(session_create_listener, sender=Session)