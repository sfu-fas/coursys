from django.db import models
from coredata.models import Member, CourseOffering
from autoslug import AutoSlugField
from grades.models import Activity
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from dashboard.models import NewsItem

class Group(models.Model):
    """
    General group information in the courses
    """
    name = models.CharField(max_length=30, help_text='Group name')
    manager = models.ForeignKey(Member, blank=False, null=False)
    courseoffering = models.ForeignKey(CourseOffering)
    #if this bool value is true, then when a new group activity is created, it will call the add_activity_to_group_auto function to create corresponding GroupMembers for that activity.
    groupForSemester = models.BooleanField(default = True)

    # preface slug with "g-" to avoid conflict with userids (so they can be used in same places in URLs)
    def autoslug(self):
        return 'g-' + str(self.name)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='courseoffering')

    def __unicode__(self):
        return '%s' % (self.name)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."

    class Meta:
        unique_together = ("name", "courseoffering")

class GroupMember(models.Model):
    """
    Member information of each group
    """
    group = models.ForeignKey(Group)
    student = models.ForeignKey(Member)
    confirmed = models.BooleanField(default = False)
    activity = models.ForeignKey(Activity)

    def __unicode__(self):
	    return '%s@%s/%s' % (self.student.person, self.group, self.activity.short_name)
    class Meta:
        unique_together = ("student", "activity")

def all_activities(members):
    """
    Return all activities for this set of group members.  i.e. all activities that any member is a member for.
    """
    return set(m.activity for m in members)

def add_activity_to_group_auto(activity, course):
    """
    if the groupForSemester bool value in Group model is true, then when a new group activity is created, it will call this add_activity_to_group_auto function to create corresponding GroupMembers for that activity.
    """
    groups = Group.objects.filter(courseoffering = course, groupForSemester = True)
    for group in groups:
	groupMembers = GroupMember.objects.filter(group = group)
	unique_students = set(groupMember.student for groupMember in groupMembers)
	for student in unique_students:
	    groupMember = GroupMember(group=group, student=student, confirmed=True, activity=activity)
	    groupMember.save()
    return

