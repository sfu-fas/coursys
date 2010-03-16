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
    
    # preface slug with "g-" to avoid conflict with userids (so they can be used in same places in URLs)
    def autoslug(self):
        return 'g-' + str(self.name)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='courseoffering')

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
