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

    def save(self, person=None, *args, **kwargs):
        super(GroupMember, self).save(*args, **kwargs)
        if self.confirmed == False:
            course = get_object_or_404(CourseOffering, slug = self.group.courseoffering.slug)
            member = get_object_or_404(Member, person = self.student.person,offering=course)
            n = NewsItem(user = person,author = self.student.person, course=member.offering,
                         source_app="Group Join", title="Group Conformation",
                         content="You have been invited to join group %s." % (self.group),
                         url=reverse('groups.views.groupmanage', kwargs={'course_slug':course.slug})
            )
            n.save()

    class Meta:
        unique_together = ("group", "student", "activity")

def all_activities(members):
    """
    Return all activities for this set of group members.  i.e. all activities that any member is a member for.
    """
    return set(m.activity for m in members)


