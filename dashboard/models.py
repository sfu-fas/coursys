from django.db import models
from coredata.models import Person, CourseOffering
from django.utils.safestring import mark_safe
from pytz import timezone
from django.conf import settings
from autoslug.settings import slugify
import random

import external.textile as textile
Textile = textile.Textile(restricted=True)

def _rfc_format(dt):
    """
    Format the datetime in RFC3339 format
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def new_feed_token():
    """
    Generate a random token for the feed URL
    """
    n = random.getrandbits(128)
    return "%x" % (n)


class NewsItem(models.Model):
    """
    Class representing a news item for a particular user.
    """
    user = models.ForeignKey(Person, null=False, related_name="user")
    author = models.ForeignKey(Person, null=True, related_name="author")
    course = models.ForeignKey(CourseOffering, null=True)
    source_app = models.CharField(max_length=20, null=False, help_text="Application that created the story")

    title = models.CharField(max_length=100, null=False, help_text="Story title (plain text)")
    content = models.TextField(help_text="Main story content (Textile markup)")
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    url = models.URLField(blank=True,verify_exists=False, help_text='absolute URL for the item: starts with "http://" or "/"')

    def content_xhtml(self):
        return mark_safe(Textile.textile(str(self.content)))

    def rfc_updated(self):
        """
        Format the updated time in RFC3339 format
        """
        tz = timezone(settings.TIME_ZONE)
        dt = self.updated
        offset = tz.utcoffset(dt)
        return _rfc_format(dt-offset)

    def feed_id(self):
        """
        Return a unique to serve as a unique Atom identifier (after being appended to the server URL).
        """
        return slugify(
            "%s %s %s" % (self.user.userid, self.published.strftime("%Y%m%d-%H%M%S"), self.id)
            )

class UserConfig(models.Model):
    """
    Simple class to hold user preferences.
    """
    user = models.ForeignKey(Person, null=False)
    key = models.CharField(max_length=20, db_index=True, null=False)
    value = models.CharField(max_length=200)
    class Meta:
        unique_together = (("user", "key"),)

    def __unicode__(self):
        return "%s: %s='%s'" % (self.user.userid, self.key, self.value)



