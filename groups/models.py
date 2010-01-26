from django.db import models
from coredata.models import Member, CourseOffering


# Create your models here.
class Group(models.Model):
    """
    General group information in the courses
    """
    name = models.CharField(maxlength=32)
    manager = models.OneToOneField(Person)
    course = models.ForeignKey(courseoffering)

    def __unicode__(self):  
        return self.name
    


class GroupMember(models.Model)
    """
    Member information of each group
    """
    group=models.ForeignKey(group)
    student= models.ForeignKey(Member)
    confirmed= models.BooleanField(default = False)
    
    
