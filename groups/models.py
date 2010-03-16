from django.db import models
from coredata.models import Member, CourseOffering
from autoslug import AutoSlugField

class Group(models.Model):
    """
    General group information in the courses
    """
    name = models.CharField(max_length=30, help_text='Group name')
    manager = models.ForeignKey(Member, blank=False, null=False)
    courseoffering = models.ForeignKey(CourseOffering)
    slug = AutoSlugField(populate_from='name', null=False, editable=False, unique_with='courseoffering')

    def __unicode__(self):  
        return '%s' % (self.name)

    class Meta:
        unique_together = ("name", "courseoffering")

class GroupMember(models.Model):
    """
    Member information of each group
    """
    group=models.ForeignKey(Group)
    student= models.ForeignKey(Member)
    confirmed= models.BooleanField(default = False)

    def __unicode__(self):
	    return '%s %s' % (self.student.person, self.group)
	
    class Meta:
        unique_together = ("group", "student")
