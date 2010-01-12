from django.db import models
from courses.coredata.models import Person
# Create your models here.

class Note(models.Model):
    student = models.ForeignKey(Person, related_name = 'std_note_set', null = False)
    advisor = models.ForeignKey(Person, related_name = 'adv_note_set', null = False)
    time_created = models.DateTimeField(null = True)
    content = models.CharField(null = True, max_length=1000) 
    hidden = models.BooleanField(null = False)
    file_uploaded = models.FileField(null = True, upload_to = "advisors_A/files/")
    # TODO: add uploaded_file here
    def __unicode__(self):
        return "student: %s, advisor: %s, on %s" % (str(self.student), str(self.advisor), str(self.time_created))
    class Meta:
        ordering = ['time_created', 'advisor', 'student']
        
from django.forms import ModelForm
from django.forms.widgets import Textarea

class NoteForm(ModelForm):
    class Meta:
        model = Note        
        exclude = ['time_created']
        # use text area for content
        widgets = {
            'content': Textarea(attrs={'cols': 80, 'rows': 10}),
        }
