from django.db import models
from django.contrib.auth import get_user_model
from oauth_provider.models import Consumer
from oauth_provider.consts import ACCEPTED

from courselib.json_fields import JSONField
from courselib.json_fields import config_property
from time import time

PERMISSION_CHOICES = [
    ('courses', 'View the courses you are enrolled in'),
    ('grades', 'View the marks you have received in your courses'),
    ('groups', 'Group memberships in your courses'),
    ('instr-info', 'Instructor-only information (read-only)'),
    ('submissions-read', 'Retrieve submissions'),
    ('submissions-write', 'Make submissions'),
    ('grades-write', 'Edit grades in courses where you are an instructor/TA'),
]
PERMISSION_OPTIONS = dict(PERMISSION_CHOICES)


class ConsumerInfo(models.Model):
    """
    Additional info about a Consumer, augmenting that model.
    """
    consumer = models.ForeignKey(Consumer)
    timestamp = models.IntegerField(default=time) # ConsumerInfo may change over time: the most recent with Token.timestamp >= ConsumerInfo.timestamp is the one the user agreed to.
    config = JSONField(null=False, blank=False, default={})
    deactivated = models.BooleanField(default=False) # kept to record user agreement, but this will allow effectively deactivating Consumers

    admin_contact = config_property('admin_contact', None) # who we can contact for this account
    permissions = config_property('permissions', []) # things this consumer can do: list of keys for PERMISSION_OPTIONS

    def __unicode__(self):
        return "info for %s at %i" % (self.consumer.key, self.timestamp)

    def permission_descriptions(self):
        return (PERMISSION_OPTIONS[p] for p in self.permissions)

    @classmethod
    def get_for_token(cls, token):
        """
        Get the ConsumerInfo that the user agreed to with this token (since it's possible the permission list changes
        over time), and return the permission list they agreed to
        """
        return ConsumerInfo.objects.filter(consumer_id=token.consumer_id, timestamp__lt=token.timestamp) \
            .order_by('-timestamp').first()

    @classmethod
    def allowed_permissions(cls, token):
        ci = ConsumerInfo.get_for_token(token)
        if not ci or ci.deactivated:
            return []
        else:
            return ci.permissions


def create_consumer(name, description, owner_userid, admin_contact, permissions):
    """
    Create a new Consumer with all of the info we need recorded. Arguments: (name, description, owner_userid, admin_contact, permissions)

    Could be rolled into a form+view in /sysadmin/, but how many could there possibly be?
    """
    assert set(permissions) <= set(PERMISSION_OPTIONS.keys()), 'Permissions must be chosen from PERMISSION_CHOICES.'

    User = get_user_model()
    c = Consumer(name=name, description=description, status=ACCEPTED,
            user=User.objects.get(username=owner_userid), xauth_allowed=False)
    c.generate_random_codes()
    c.save()

    i = ConsumerInfo(consumer=c)
    i.admin_contact = admin_contact
    i.permissions = list(permissions)
    i.save()

    print("Consumer key:", c.key)
    print("Consumer secret:", c.secret)

