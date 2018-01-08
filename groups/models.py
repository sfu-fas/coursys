from django.db import models
from coredata.models import Member, CourseOffering, repo_name
from autoslug import AutoSlugField
from grades.models import *
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from dashboard.models import NewsItem
from django.conf import settings
from courselib.slugs import make_slug
from courselib.svn import update_group_repository
import datetime, urllib.parse


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
        return 'g-' + make_slug(self.name)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='courseoffering')
    svn_slug = AutoSlugField(max_length=17, populate_from='slug', null=True, editable=False, unique_with='courseoffering')

    def __unicode__(self):
        return '%s' % (self.name)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def get_absolute_url(self):
        return reverse('offering:groups:view_group', kwargs={'course_slug': self.courseoffering.slug,
                                                          'group_slug': self.slug})

    def confirmed_members(self):
        return self.groupmember_set.filter(confirmed=True).select_related('student__person')

    def svn_url(self):
        "SVN URL for this member (assuming offering.uses_svn())"
        return urllib.parse.urljoin(settings.SVN_URL_BASE, repo_name(self.courseoffering, self.svn_slug))

    class Meta:
        unique_together = (("name", "courseoffering"), ("slug", "courseoffering"), ("svn_slug", "courseoffering"))
        ordering = ["name"]

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
        ordering = ["student__person", "activity"]

    def save(self, *args, **kwargs):
        super(GroupMember, self).save(*args, **kwargs)
        # update group's SVN repo
        if settings.SVN_DB_CONNECT: # don't try if not configured
            update_group_repository(self.group.courseoffering, self.group)

    def student_editable(self, userid):
        """
        Is this student allowed to modify this membership?  Returns text reason for non-editable (or "" if allowed)
        """
        # is student actually a member for this activity (i.e. must be part of group for assignment 3 to remove another for assignment 3)
        user_membership = self.group.groupmember_set.filter(student__person__userid=userid, activity=self.activity)
        if not user_membership:
            return "you are not a member for " + self.activity.short_name
        
        # if due date passed: not editable.
        if self.activity.due_date and self.activity.due_date < datetime.datetime.now():
            return "due date passed"

        # if student has a grade: not editable.
        if isinstance(self.activity, LetterActivity):
            GradeClass = LetterGrade
        else:
            GradeClass = NumericGrade
        grades = GradeClass.objects.filter(activity=self.activity, member=self.student).exclude(flag="NOGR")
        if len(grades)>0:
            return "grade received"
        
        # if there has been a submission: not editable
        from submission.models import GroupSubmission
        subs = GroupSubmission.objects.filter(group=self.group, activity=self.activity)
        if len(subs) > 0:
            return "submission made"
        
        return ""

def all_activities(members):
    """
    Return all activities for this set of group members.  i.e. all activities that any member is a member for.
    """
    return set(m.activity for m in members if m.activity.deleted==False)


def add_activity_to_group(activity1, activity2, course):
    """
    copy group settings from activity2 -> activity1
    """
    groups = Group.objects.filter(courseoffering = course)
    for group in groups:
        groupMembers = GroupMember.objects.filter(group=group, activity=activity2, confirmed=True)
        unique_students = set(groupMember.student for groupMember in groupMembers)
        for student in unique_students:
            groupMember = GroupMember(group=group, student=student, confirmed=True, activity=activity1)
            groupMember.save()
