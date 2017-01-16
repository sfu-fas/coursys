# based on http://stackoverflow.com/a/4631504/1236542

import sys

from django.db import models
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.signals import user_logged_in, user_logged_out

from django.db.models.signals import post_save
from django.utils import timezone

from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice

from six.moves.urllib.parse import quote, urlencode
import base64

ALL_DEVICES = [TOTPDevice, StaticDevice]

NEVER_AUTH = sys.maxint

OTP_AUTH_AGE = getattr(settings, 'OTP_AUTH_AGE', 1000)
OTP_2FA_AGE = getattr(settings, 'OTP_2FA_AGE', 10000)


def all_otp_devices(user, confirmed=True):
    for Dev in ALL_DEVICES:
        devs = Dev.objects.devices_for_user(user, confirmed=confirmed)
        for d in devs: # could be a python3 'yield from'
            yield d


def totpauth_url(totp_dev):
    # https://github.com/google/google-authenticator/wiki/Key-Uri-Format
    accountname = totp_dev.user.username.encode('utf8')

    label = accountname

    query = [
        ('secret', base64.b32encode(totp_dev.bin_key)),
        ('digits', totp_dev.digits),
        ('issuer', b'CourSys')
    ]

    return 'otpauth://totp/%s?%s' % (label, urlencode(query))


class SessionInfo(models.Model):
    session_key = models.CharField(max_length=40, primary_key=True)
    created = models.DateTimeField(auto_now_add=True)
    last_auth = models.DateTimeField(null=True)
    last_2fa = models.DateTimeField(null=True)

    @classmethod
    def for_session_key(cls, session_key, save_new=True):
        'Retrieve or create a SessionInfo for this session_key.'
        try:
            si = cls.objects.get(session_key=session_key)
        except (SessionInfo.DoesNotExist):
            si = SessionInfo(session_key=session_key)
            if save_new:
                si.save()

        return si

    @classmethod
    def for_request(cls, request, save_new=True, user=None):
        'Retrieve the SessionInfo for this request, if it has an active session.'
        if hasattr(request, 'session_info') and request.session_info is not None:
            # already have it.
            return request.session_info

        if isinstance(user, AnonymousUser) or request.session.session_key is None:
            # no logged-in session: no point in looking.
            request.session_info = None
            return None

        si = cls.for_session_key(request.session.session_key, save_new=save_new)

        request.session_info = si
        return si

    @classmethod
    def just_logged_in(cls, request):
        'Records that the session associated with this request just logged in.'
        si = cls.for_request(request, save_new=False)
        si.last_auth = timezone.now()
        si.save()
        return si

    @classmethod
    def just_logged_out(cls, request):
        'Records that the session associated with this request just logged out.'
        si = cls.for_request(request, save_new=False)
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

    def __unicode__(self):
        return '%s@%s' % (self.session_key, self.created)

    def okay_age_auth(self, user):
        'Is the age of the standard Django auth okay for this user?'
        if self.last_auth:
            age = (timezone.now() - self.last_auth).total_seconds()
            return age <= OTP_AUTH_AGE
        else:
            return False

    def okay_age_2fa(self, user):
        'Is the age of the 2FA/OTP validation okay for this user?'
        if self.last_2fa:
            age = (timezone.now() - self.last_2fa).total_seconds()
            return age <= OTP_2FA_AGE
        else:
            return False


def logged_in_listener(request, **kwargs):
    SessionInfo.just_logged_in(request)

def logged_out_listener(request, **kwargs):
    SessionInfo.just_logged_out(request)

user_logged_in.connect(logged_in_listener)
user_logged_out.connect(logged_out_listener)

def session_create_listener(instance, **kwargs):
    instance.session_info = SessionInfo.for_session_key(instance.session_key)

post_save.connect(session_create_listener, sender=Session)