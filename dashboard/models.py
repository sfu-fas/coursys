from django.db import models
from coredata.models import Person, CourseOffering, Member
from django.utils.safestring import mark_safe
from pytz import timezone
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from autoslug.settings import slugify
from courselib.json_fields import JSONField, config_property
from courselib.branding import product_name
from courselib.storage import UploadedFileStorage, upload_path
import random, hashlib, os, datetime


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
    user = models.ForeignKey(Person, null=False, related_name="user", on_delete=models.PROTECT)
    author = models.ForeignKey(Person, null=True, related_name="author", on_delete=models.PROTECT)
    course = models.ForeignKey(CourseOffering, null=True, on_delete=models.PROTECT)
    source_app = models.CharField(max_length=20, null=False, help_text="Application that created the story")

    title = models.CharField(max_length=100, null=False, help_text="Story title (plain text)")
    content = models.TextField(help_text=mark_safe('Main story content'))
    published = models.DateTimeField(default=datetime.datetime.now)
    updated = models.DateTimeField(auto_now=True)
    url = models.URLField(blank=True, verbose_name="URL", help_text='absolute URL for the item: starts with "http://" or "/"')
    
    read = models.BooleanField(default=False, help_text="The user has marked the story read")
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:
        # 'markup': markup language used: see courselib/markup.py
        # 'math': page uses MathJax? (boolean)

    markup = config_property('markup', 'creole')
    math = config_property('math', False)

    def __str__(self):
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
            return settings.DEFAULT_FROM_EMAIL
    
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
        if not self.user.email():
            return

        headers = {
                'Precedence': 'bulk',
                'Auto-Submitted': 'auto-generated',
                'X-coursys-topic': self.source_display(),
                }

        if self.course:
            subject = "%s: %s" % (self.course.name(), self.title)
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
            url = settings.BASE_ABS_URL + reverse('news:news_list')
        
        text_content = "For more information, see " + url + "\n"
        text_content += "\n--\nYou received this email from %s. If you do not wish to receive\nthese notifications by email, you can edit your email settings here:\n  " % (product_name(hint='course'))
        text_content += settings.BASE_ABS_URL + reverse('config:news_config')
        
        if self.course:
            html_content = '<h3>%s: <a href="%s">%s</a></h3>\n' % (self.course.name(), url, self.title)
        else:
            html_content = '<h3><a href="%s">%s</a></h3>\n' % (url, self.title)
        html_content += self.content_xhtml()
        html_content += '\n<p style="font-size: smaller; border-top: 1px solid black;">You received this email from %s. If you do not wish to receive\nthese notifications by email, you can <a href="%s">change your email settings</a>.</p>' \
                        % (product_name(hint='course'), settings.BASE_ABS_URL + reverse('config:news_config'))
        
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email], headers=headers)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
    def content_xhtml(self):
        """
        Render content field as XHTML.
        """
        from courselib.markup import markup_to_html
        return markup_to_html(self.content, self.markup, html_already_safe=False, restricted=True)

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

        markup = newsitem_kwargs.pop('markup', 'textile')
        for m in members:
            n = NewsItem(user=m.person, **newsitem_kwargs)
            n.markup = markup
            n.save()


class UserConfig(models.Model):
    """
    Simple class to hold user preferences.
    """
    user = models.ForeignKey(Person, null=False, on_delete=models.PROTECT)
    key = models.CharField(max_length=20, db_index=True, null=False)
    value = JSONField(null=False, blank=False, default=dict)
    class Meta:
        unique_together = (("user", "key"),)

    def __str__(self):
        return "%s: %s='%s'" % (self.user.userid, self.key, self.value)


def _sig_upload_to(instance, filename):
    """
    path to upload case attachment
    """
    return upload_path('signatures', filename)


class Signature(models.Model):
    """
    User's signature (for letters)
    """
    user = models.ForeignKey(Person, null=False, on_delete=models.PROTECT)
    sig = models.FileField(upload_to=_sig_upload_to, storage=UploadedFileStorage, max_length=500)
    resolution = 200 # expect 200 dpi images
    
    def __str__(self):
        return "Signature of %s" % (self.user.name())
