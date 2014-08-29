from django.db import models
from oauth_provider.models import Consumer, Token
from courselib.json_fields import JSONField
from courselib.json_fields import config_property

PERMISSION_CHOICES = [
    ('courses', 'View the courses you are enrolled in'),
    ('grades', 'View the marks you have received in your courses')
]
PERMISSION_OPTIONS = dict(PERMISSION_CHOICES)


class ConsumerInfo(models.Model):
    """
    Additional info about a Consumer, augmenting that model.
    """
    consumer = models.ForeignKey(Consumer, unique=True)
    config = JSONField(null=False, blank=False, default={})

    admin_contact = config_property('admin_contact', None) # who we can contact for this account
    permissions = config_property('permissions', []) # things this consumer can do: list of keys for PERMISSION_OPTIONS

    def permission_descriptions(self):
        return (PERMISSION_OPTIONS[p] for p in self.permissions)


class TokenInfo(models.Model):
    """
    Additional info about a Token, augmenting that model.
    """
    token = models.ForeignKey(Token, unique=True)
    config = JSONField(null=False, blank=False, default={})

    permissions = config_property('permissions', []) # things user agreed to: list of keys for PERMISSION_OPTIONS

    def permission_descriptions(self):
        return (PERMISSION_OPTIONS[p] for p in self.permissions)
