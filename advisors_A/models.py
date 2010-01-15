from django.db import models
from courses.coredata.models import Person
from django.template.defaultfilters import default
# Create your models here.

class Note(models.Model):
    student = models.ForeignKey(Person, related_name = 'std_note_set', null = False)
    advisor = models.ForeignKey(Person, related_name = 'adv_note_set', null = False)
    time_created = models.DateTimeField(null = False)    
    content = models.TextField(null = True, max_length=1000, blank=True)     
    file_uploaded = models.FileField(null = True, upload_to = "advisors_A/files/%Y/%m/%d'", blank=True)   
    hidden = models.BooleanField(null = False, default = False)
    def hide(self):
        """
        set hidden flag
        """
        self.hidden = True
        self.save()    
    def __unicode__(self):
        return "student: %s, advisor: %s, on %s" % (str(self.student), str(self.advisor), str(self.time_created))
    class Meta:
        ordering = ['time_created', 'advisor', 'student']
        
from django.forms import ModelForm
class NoteForm(ModelForm):
    class Meta:
        model = Note            
        # these 3 fields are decided from the request ant the time the form is submitted
        exclude = ['student', 'advisor', 'time_created']
        
        
