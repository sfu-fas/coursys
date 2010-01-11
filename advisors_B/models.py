from django.db import models
import datetime
from courses.coredata.models import Person, OtherUser

class Note(models.Model):
    """
    A Note in the system (with particular student, creation date and author)
    """
    Content = models.CharField(max_length = 1000)
    Student = models.ForeignKey(Person)
    CreateDate = models.DateTimeField('create date')
    Author = models.ForeignKey(OtherUser)
    #file attachment
    Hidden = models.BooleanField(default = False)


    def __unicode__(self):
        return "%s , %s " % (str(self.CreateDate) , str(self.Student))

    def AssignDate(self):
        self.CreateDate = datetime.date.today()
        return





