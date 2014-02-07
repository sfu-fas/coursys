from django.db import models
from grades.models import Activity
from coredata.models import Member, Person,CourseOffering
from groups.models import Group,GroupMember
from datetime import datetime
from autoslug import AutoSlugField
from django.db.models import Max
from dashboard.models import NewsItem
from django.core.urlresolvers import reverse
import os.path
from django.conf import settings
from django.utils.safestring import mark_safe
from courselib.slugs import make_slug


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
    def autoslug(self):
        return make_slug(self.title)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='activity')
    deleted = models.BooleanField(default=False, help_text="Component is invisible to students and can't be submitted if checked.")
    specified_filename = models.CharField(max_length=200, help_text="Specify a file name for this component.")

    def __cmp__(self, other):
        return cmp(self.position, other.position)
    class Meta:
        ordering = ['position']
        app_label = 'submission'
    def __unicode__(self):
        return "%s %s"%(self.title, self.description)
    def visible_type(self):
        "Should this componet type be visible to allow creation of new components (or soft-deleted)?"
        return True
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
        
    def save(self, **kwargs):
        if self.position is None:
            lastpos = SubmissionComponent.objects.filter(activity=self.activity) \
                    .aggregate(Max('position'))['position__max']
            if lastpos is None:
                lastpos = 0
            self.position = lastpos+1
        super(SubmissionComponent, self).save(**kwargs)




# per-submission models, created when a student/group submits an assignment:

class Submission(models.Model):
    """
    A student's or group's submission for an activity
    """
    activity = models.ForeignKey(Activity)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(Member, null=True, help_text = "TA or instructor that will mark this submission")
    status = models.CharField(max_length=3, null=False,choices=STATUS_CHOICES, default = "NEW")
    def __cmp__(self, other):
        return cmp(other.created_at, self.created_at)
    class Meta:
        ordering = ['-created_at']
        app_label = 'submission'
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."

    "Set ownership, and make state = in progree "
    def set_owner(self, course, userid):
        member = Member.objects.filter(person__userid = userid).filter(offering = course)
        if member:
            self.owner = member[0]
            self.status = "INP"
            self.save()

class StudentSubmission(Submission):
    member = models.ForeignKey(Member, null=False)
    class Meta:
        app_label = 'submission'
    def get_userid(self):
        return self.member.person.userid
    def __unicode__(self):
        return "%s->%s@%s" % (self.member.person.userid, self.activity, self.created_at)
    def short_str(self):
        return "%s submission by %s at %s" % (self.activity.short_str(), self.member.person.userid, self.created_at.strftime("%Y-%m-%d %H:%M"))
    def get_absolute_url(self):
        return reverse('submission.views.show_components_submission_history', kwargs={'course_slug': self.member.offering.slug, 'activity_slug': self.activity.slug, 'userid': self.member.person.userid})
    def file_slug(self):
        return self.member.person.userid or str(self.member.person.emplid)

class GroupSubmission(Submission):
    group = models.ForeignKey(Group, null=False)
    creator = models.ForeignKey(Member, null = False)

    class Meta:
        app_label = 'submission'
    def get_userid(self):
        return self.group.manager.person.userid
    def __unicode__(self):
        return "%s->%s@%s" % (self.group.manager.person.userid, self.activity, self.created_at)
    def short_str(self):
        return "%s submission by %s for group %s at %s" % (self.activity.short_str(), self.creator.person.userid, self.group.name, self.created_at.strftime("%Y-%m-%d %H:%M"))
    def get_absolute_url(self):
        return reverse('submission.views.show_components_submission_history', kwargs={'course_slug': self.group.courseoffering.slug, 'activity_slug': self.activity.slug, 'userid': self.creator.person.userid})
    def file_slug(self):
        return self.group.slug

    def save(self):
        new_submit = (self.id is None)
        super(GroupSubmission, self).save()
        if new_submit:
            member_list = GroupMember.objects.filter(group=self.group, activity=self.activity)
            for member in member_list:
                n = NewsItem(user = member.student.person, author=self.creator.person, course=member.group.courseoffering,
                    source_app="submit_group", title="New Group Submission",
                    content="Your group member %s has made a submission for %s."
                        % (self.creator.person.name(), self.activity.name),
                    url=reverse('submission.views.show_components', kwargs={'course_slug': self.group.courseoffering.slug, 'activity_slug': member.activity.slug})
                    )
                n.save()


# parts of a submission, created as part of a student/group submission

def submission_upload_path(instance, filename):
    """
    Return the filename to upload any submitted file.
    """
    fullpath = os.path.join(
            instance.component.activity.offering.slug,
            instance.component.activity.slug,
            instance.submission.file_slug(),
            instance.submission.created_at.strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.submission.id),
            instance.component.slug,
            filename.encode('ascii', 'ignore'))
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
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    def __cmp__(self, other):
        return cmp(other.submit_time, self.submit_time)
    class Meta:
        ordering = ['submit_time']
        app_label = 'submission'
    def get_size_in_kb(self):
        res = int(self.get_size())/1024
        return res
    def get_submitter(self):
        group = GroupSubmission.objects.filter(id=self.submission.id)
        if len(group) is 0:
            student = StudentSubmission.objects.filter(id=self.submission.id)
            return student.member.person
        return group[0].creator.person
    def __unicode__(self):
        return "%s@%s" % (self.submission.activity, self.submission.created_at)

    def sendfile(self, upfile, response):
        """
        Send the contents of the file as the response, given a FileField object to read from.
        """
        path, filename = os.path.split(upfile.name)
        response['Content-Disposition'] = 'inline; filename="' + filename + '"'
        try:
            fh = open(upfile.path, "r")
        except IOError:
            response['Content-type'] = "text/plain"
            response.write("File missing. It has likely been archived.")
            return

        for data in fh:
            response.write(data)

    def file_filename(self, upfile, prefix=None):
        """
        Come up with a filename for the uploaded file in a ZIP archive.
        """
        filename = os.path.split(upfile.name)[1]
        if prefix:
            filename = os.path.join(prefix, filename)
        return filename

