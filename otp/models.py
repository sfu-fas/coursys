# based on http://stackoverflow.com/a/4631504/1236542

import sys

from django.db import models
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.signals import user_logged_in

from django.db.models.signals import post_save
from django.utils import timezone

NEVER_AUTH = 100000 #sys.maxint

class SessionInfo(models.Model):
    session = models.OneToOneField(Session, db_index=True, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    last_auth = models.DateTimeField(null=True)
    last_2fa = models.DateTimeField(null=True)

    @classmethod
    def for_session(cls, session, save_new=True):
        try:
            return cls.objects.get(session=session.session_key)
        except (SessionInfo.DoesNotExist):
            si = SessionInfo(session=session)
            if save_new:
                si.save()
            return si

    @classmethod
    def just_logged_in(cls, session):
        si = cls.for_session(session, save_new=False)
        si.last_auth = timezone.now()
        si.save()

    def __unicode__(self):
        return '%s@%s' % (self.session, self.created)

    def age(self):
        'Age of the session, in seconds.'
        return (timezone.now() - self.created)

    def age_auth(self):
        'Age of the standard authentication on the session, in seconds.'
        return (timezone.now() - self.last_auth) if self.last_auth else NEVER_AUTH

    def age_2fa(self):
        'Age of the second-factor authentication on the session, in seconds.'
        return (timezone.now() - self.last_2fa) if self.last_2fa else NEVER_AUTH



def logged_in_listener(instance, user, request, **kwargs):
    SessionInfo.just_logged_in(request.session)

#user_logged_in.connect(logged_in_listener)


def session_create_listener(instance, **kwargs):
    store = SessionStore(session_key=instance.session_key)

    if '_auth_user_id' in store:
        try:
            instance.sessioninfo
        except SessionInfo.DoesNotExist:
            sessioninfo = SessionInfo(session=instance)
            sessioninfo.save()

post_save.connect(session_create_listener, sender=Session)