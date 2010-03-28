from django.db import models
from grades.models import Activity
from coredata.models import Member, Person,CourseOffering
#from courses.grades.models import slug
from groups.models import Group,GroupMember
from datetime import datetime
from autoslug import AutoSlugField
from django.db.models import Max
from dashboard.models import NewsItem
from django.core.urlresolvers import reverse
import os.path
from django.conf import settings


STATUS_CHOICES = [
    ('NEW', 'New'),
    ('INP', 'In-Progress'),
    ('DON', 'Marked') ]

from django.core.files.storage import FileSystemStorage
SubmissionSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

# per-activity models, defined by instructor:

class SubmissionComponent(models.Model):
    """
    A component of the activity that will be submitted by students
    """
    activity = models.ForeignKey(Activity)
    title = models.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")')
    description = models.CharField(max_length=1000, help_text="Short explanation for this component.", null=True,blank=True)
    position = models.PositiveSmallIntegerField(help_text="The order of display for listing components.", null=True,blank=True)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with='activity')

    def __cmp__(self, other):
        return cmp(self.position, other.position)
    class Meta:
        ordering = ['position']
        app_label = 'submission'
    def __unicode__(self):
        return "%s[%s]%s"%(self.title, self.get_type(), self.description)
    def get_type(self):
        "Return xxx of xxxComponent as type"
        class_name = self.__class__.__name__
        return class_name[:class_name.index("Component")]
        
    def save(self):
        if self.position is None:
            lastpos = SubmissionComponent.objects.filter(activity=self.activity) \
                    .aggregate(Max('position'))['position__max']
            if lastpos is None:
                lastpos = 0
            self.position = lastpos+1
        super(SubmissionComponent, self).save()




# per-submission models, created when a student/group submits an assignment:

class Submission(models.Model):
    """
    A student's or group's submission for an activity
    """
    activity = models.ForeignKey(Activity)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(Member, null=True, help_text = "TA or instructor that will mark this submission")
    status = models.CharField(max_length=3, null=False,choices=STATUS_CHOICES, default = "NEW")
    class Meta:
        app_label = 'submission'

    "Set ownership, and make state = in progree "
    def set_owner(self, course, userid):
        member = Member.objects.filter(person__userid = userid).filter(offering = course)
        if member != []:
            self.owner = member[0]
            self.status = "INP"
            self.save()
    def get_type(self):
        g = GroupSubmission.objects.filter(pk = self.pk)
        if len(g) > 0:
            return "Group"
        return "student"
    def get_derived_class(self):
        if self.get_type() == "Group":
            return GroupSubmission.objects.all().get(pk = self.pk)
        else:
            return StudentSubmission.objects.all().get(pk = self.pk)
    def get_userid(self):
        return self.get_derived_class().get_userid()

class StudentSubmission(Submission):
    member = models.ForeignKey(Member, null=False)
    class Meta:
        app_label = 'submission'
    def get_userid(self):
        return self.member.person.userid
    def __unicode__(self):
        return "%s->%s@%s" % (self.member.person.userid, self.activity, self.created_at)

class GroupSubmission(Submission):
    group = models.ForeignKey(Group, null=False)
    creator = models.ForeignKey(GroupMember, null = False)

    class Meta:
        app_label = 'submission'
    def get_userid(self):
        return self.group.manager.person.userid
    def __unicode__(self):
        return "%s->%s@%s" % (self.group.manager.person.userid, self.activity, self.created_at)

    def save(self):
        super(GroupSubmission, self).save()
        member_list = GroupMember.objects.exclude(student = self.creator).filter(group = self.group)
        for member in member_list:
            n = NewsItem(user = member.student.person, author=self.creator.student.person, course=member.group.courseoffering,
                source_app="group submission", title="New Group Submission",
                content="Your group member %s has made a submission for %s."
                    % (self.creator.student.person.name(), self.activity.name),
                url=reverse('submission.views.show_components', kwargs={'course_slug': self.group.courseoffering.slug, 'activity_slug': member.activity.slug})
                )
            n.save()


# parts of a submission, created as part of a student/group submission

def submission_upload_path(instance, filename):
    """
    Return the filename to upload any submitted file.
    """
    if hasattr(instance.submission, 'group'):
        # a group submission: use the group slug to identify
        usergroup = instance.submission.group.slug
    else:
        # an individual submission: use the userid to identify
        usergroup = instance.submission.member.person.userid

    fullpath = os.path.join(
            settings.SUBMISSION_PATH,
            instance.component.activity.offering.slug,
            instance.component.activity.slug,
            usergroup,
            instance.submission.created_at.strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.submission.id),
            instance.component.slug,
            filename)
    return fullpath


class SubmittedComponent(models.Model):
    """
    Part of a student's/group's submission
    """
    submission = models.ForeignKey(Submission)
    submit_time = models.DateTimeField(auto_now_add = True)
    def get_time(self):
        "return the submit time of the component"
        return self.submit_time.strftime("%Y-%m-%d %H:%M:%S")
    def get_late_time(self):
        "return how late the submission is"
        time = self.submission.create_at - self.activity.due_date
        if time < datetime.datedelta():
            return 0
        else:
            return time
    def __cmp__(self, other):
        return cmp(other.submit_time, self.submit_time)
    class Meta:
        ordering = ['submit_time']
        app_label = 'submission'
    def get_type(self):
        "Return xxx of Submittedxxx as type"
        class_name = self.__class__.__name__
        return class_name[9:]
    def get_size_in_kb(self):
        res = int(self.get_size())/1024
        return res
    def __unicode__(self):
        return "[%s] %s->%s@%s" % (self.get_type(), self.submission.get_userid(), self.submission.activity, self.submission.created_at)


