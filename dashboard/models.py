from django.db import models
from coredata.models import Person, CourseOffering, Member
from django.utils.safestring import mark_safe
from pytz import timezone
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from autoslug.settings import slugify
from jsonfield import JSONField
import random, hashlib, os

import textile
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
    random.seed()
    n = random.getrandbits(128)
    return "%032x" % (n)


class NewsItem(models.Model):
    """
    Class representing a news item for a particular user.
    """
    user = models.ForeignKey(Person, null=False, related_name="user")
    author = models.ForeignKey(Person, null=True, related_name="author")
    course = models.ForeignKey(CourseOffering, null=True)
    source_app = models.CharField(max_length=20, null=False, help_text="Application that created the story")

    title = models.CharField(max_length=100, null=False, help_text="Story title (plain text)")
    content = models.TextField(help_text=mark_safe('Main story content (<a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a>)'))
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    url = models.URLField(blank=True, verbose_name="URL", help_text='absolute URL for the item: starts with "http://" or "/"')
    
    read = models.BooleanField(default=False, help_text="The user has marked the story read")
    
    def __unicode__(self):
        return '"%s" for %s' % (self.title, self.user.userid)
    
    def save(self, *args, **kwargs):
        super(NewsItem, self).save(*args, **kwargs)

        # see if this user wants news by email
        ucs = UserConfig.objects.filter(user=self.user, key="newsitems")
        if ucs and 'email' in ucs[0].value and not ucs[0].value['email']:
            # user has requested no email
            pass
        else:
            self.email_user()

    def email_from(self):
        """
        Determine who the email should appear to come from: perfer to use course contact email if exists.
        """
        if self.course and self.course.taemail():
            if self.author:
                return "%s <%s> (per %s)" % (self.course.name(), self.course.taemail(), self.author.name())
            else:
                return "%s <%s>" % (self.course.name(), self.course.taemail())
        elif self.author:
            return self.author.full_email()
        else:
            return "CourSys <%s>" % (settings.DEFAULT_FROM_EMAIL)
    
    # turn the source_app field into a more externally-friendly string
    source_app_translate = {
            'dashboard': 'typed',
            'group submission': 'submit_group',
            }
    def source_display(self):
        if self.source_app in self.source_app_translate:
            return self.source_app_translate[self.source_app]
        else:
            return self.source_app
    
    def email_user(self):
        """
        Email this news item to the user.
        """
        headers = {
                'Precedence': 'bulk',
                'Auto-Submitted': 'auto-generated',
                'X-coursys-topic': self.source_display(),
                }

        if self.course:
            subject = u"%s: %s" % (self.course.name(), self.title)
            headers['X-course'] = self.course.slug
        else:
            subject = self.title
        to_email = self.user.full_email()
        from_email = self.email_from()
        if self.author:
            headers['Sender'] = self.author.email()
        else:
            headers['Sender'] = settings.DEFAULT_SENDER_EMAIL

        if self.url:
            url = self.absolute_url()
        else:
            url = settings.BASE_ABS_URL + reverse('dashboard.views.news_list')
        
        text_content = u"For more information, see " + url + "\n"
        text_content += u"\n--\nYou received this email from CourSys. If you do not wish to receive\nthese notifications by email, you can edit your email settings here:\n  "
        text_content += settings.BASE_ABS_URL + reverse('dashboard.views.news_config')
        
        if self.course:
            html_content = u'<h3>%s: <a href="%s">%s</a></h3>\n' % (self.course.name(), url, self.title)
        else:
            html_content = u'<h3><a href="%s">%s</a></h3>\n' % (url, self.title)
        html_content += self.content_xhtml()
        html_content += u'\n<p style="font-size: smaller; border-top: 1px solid black;">You received this email from CourSys. If you do not wish to receive\nthese notifications by email, you can <a href="' + settings.BASE_ABS_URL + reverse('dashboard.views.news_config') + '">change your email settings</a>.</p>'
        
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email], headers=headers)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        
        
    def content_xhtml(self):
        """
        Render content field as XHTML.
        
        Memoized in the cache: textile is expensive.
        """
        key = "news-content-" + hashlib.md5(self.content.encode("utf-8")).hexdigest()
        val = cache.get(key)
        if val:
            return mark_safe(val)
        
        markup = mark_safe(Textile.textile(unicode(self.content)))

        cache.set(key, markup, 86400)
        return markup

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
    
    def absolute_url(self):
        """
        Return an absolute URL (scheme+server+path) for this news item.
        """
        if self.url.startswith("/"):
            return settings.BASE_ABS_URL + self.url
        else:
            return self.url
    
    @classmethod
    def for_members(cls, member_kwargs, newsitem_kwargs):
        """
        Create a news item for Members identified by member_kwards (role=DROP excluded
        automatically). Details of Newsitem (except person) should be specified by
        newsitem_kwargs.
        """
        # randomize order in the hopes of throwing off any spam filters
        members = Member.objects.exclude(role="DROP").exclude(role="APPR").filter(**member_kwargs)
        members = list(members)
        random.shuffle(members)
        
        for m in members:
            n = NewsItem(user=m.person, **newsitem_kwargs)
            n.save()


class UserConfig(models.Model):
    """
    Simple class to hold user preferences.
    """
    user = models.ForeignKey(Person, null=False)
    key = models.CharField(max_length=20, db_index=True, null=False)
    value = JSONField(null=False, blank=False, default={})
    class Meta:
        unique_together = (("user", "key"),)

    def __unicode__(self):
        return "%s: %s='%s'" % (self.user.userid, self.key, self.value)

from django.core.files.storage import FileSystemStorage
SignatureStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

def _sig_upload_to(instance, filename):
    """
    path to upload case attachment
    """
    fullpath = os.path.join(
        "signatures",
        str(instance.user.userid),
        filename.encode('ascii', 'ignore'))
    return fullpath


class Signature(models.Model):
    """
    User's signature (for letters)
    """
    user = models.ForeignKey(Person, null=False)
    sig = models.FileField(upload_to=_sig_upload_to, storage=SignatureStorage, max_length=500)
    resolution = 200 # expect 200 dpi images
    
    def __unicode__(self):
        return "Signature of %s" % (self.user.name())
