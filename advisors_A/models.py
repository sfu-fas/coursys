from django.db import models
from courses.coredata.models import Person
# Create your models here.

class Note(models.Model):
    student = models.ForeignKey(Person, related_name = 'std_note_set', null = False)
    advisor = models.ForeignKey(Person, related_name = 'adv_note_set', null = False)
    time_created = models.DateTimeField(null = False)
    content = models.CharField(null = True, max_length=1000) 
    hidden = models.BooleanField(null = False)
    # add uploaded_file here
    def __unicode__(self):
        return "student: %s, advisor: %s, on %s" % (str(self.student), str(self.advisor), str(self.time_created))
    class Meta:
        ordering = ['time_created']