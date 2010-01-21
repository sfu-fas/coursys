from django.db import models

from django.template.defaultfilters import slugify

from timezones.fields import TimeZoneField
from coredata.models import Person, Role
from django.forms import ModelForm

class Note(models.Model):
    """
    A Note in the system (with particular student, creation date and author)
    """
    content = models.CharField(max_length = 1000)
    student = models.ForeignKey(Person)
    create_date = models.DateTimeField('create date')
    author = models.ForeignKey(Role)
    hidden = models.BooleanField(default = False)
    file = models.FileField(upload_to='UploadFile/', blank = True)


    def __unicode__(self):
        return "%s\t%s\t%s... " % (str(self.create_date.date()) , str(self.student),str(self.content)[:20])

    def assign_date(self):
        self.create_date = datetime.date.today()
        return

class NoteForm(ModelForm):
    class Meta:
        model = Note
