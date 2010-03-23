from django.db import models
from coredata.models import Person, CourseOffering
from django.utils.html import escape

#import textile
#Textile = textile.Textile(restricted=True)

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

    #def content_xhtml(self):
    #    return Textile.textile(str(self.content))

from django.forms import ModelForm
class MessageForm(ModelForm):
    class Meta:
        model = NewsItem
        # these 3 fields are decided from the request ant the time the form is submitted
        exclude = ['user', 'author', 'published','updated','source_app','course']

