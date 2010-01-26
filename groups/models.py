from django.db import models
from coredata.models import Member, CourseOffering


# Create your models here.
class Group(models.Model):
    """
    General group information in the courses
    """
    name = models.CharField(max_length=30, help_text='Group name')
    manager = models.OneToOneField(Member, blank = True)
    courseoffering = models.ForeignKey(CourseOffering)

    def __unicode__(self):  
        return '%s' % (self.name)

class GroupMember(models.Model):
    """
    Member information of each group
    """
    group=models.ForeignKey(Group)
    student= models.ForeignKey(Member)
    confirmed= models.BooleanField(default = False)

    def __unicode__(self):
	    return '%s %s' % (self.student.person, self.group)
    
    
