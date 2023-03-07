import hashlib
from typing import Optional

from django.db import models
from django.core.validators import MaxValueValidator
from django.db.models.fields.files import FieldFile
from django.dispatch import receiver
from grades.models import Activity
from coredata.models import Member, Person,CourseOffering
from groups.models import Group,GroupMember
from datetime import datetime, timedelta
from autoslug import AutoSlugField
from django.db.models import Max
from dashboard.models import NewsItem
from django.urls import reverse
import os.path
from django.conf import settings
from django.utils.safestring import mark_safe
from courselib.slugs import make_slug
from courselib.storage import upload_path, UploadedFileStorage
from courselib.json_fields import JSONField, config_property


STATUS_CHOICES = [
    ('NEW', 'New'),
    ('INP', 'In-Progress'),
    ('DON', 'Marked') ]


# per-activity models, defined by instructor:

class SubmissionComponent(models.Model):
    """
    A component of the activity that will be submitted by students
    """
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    title = models.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")')
    description = models.CharField(max_length=1000, help_text="Short explanation for this component.", null=True,blank=True)
    position = models.PositiveSmallIntegerField(help_text="The order of display for listing components.", null=True,blank=True)
    def autoslug(self):
        return make_slug(self.title)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='activity')
    deleted = models.BooleanField(default=False, help_text="Component is invisible to students and can't be submitted if checked.")
    specified_filename = models.CharField(max_length=200, help_text="Specify a file name for this component.")

    error_messages = {}

    def __lt__(self, other):
        return self.position < other.position
    class Meta:
        ordering = ['position']
        app_label = 'submission'
    def __str__(self):
        return "%s %s"%(self.title, self.description)
    def visible_type(self):
        "Should this componet type be visible to allow creation of new components (or soft-deleted)?"
        return True
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
        
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
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(Member, null=True, help_text = "TA or instructor that will mark this submission", on_delete=models.PROTECT)
    status = models.CharField(max_length=3, null=False,choices=STATUS_CHOICES, default = "NEW")
    def __lt__(self, other):
        return other.created_at < self.created_at
    class Meta:
        ordering = ['-created_at']
        app_label = 'submission'
    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")

    def set_owner(self, course, userid):
        "Set ownership, and make state = in progree "
        member = Member.objects.filter(person__userid = userid).filter(offering = course)
        if member:
            self.owner = member[0]
            self.status = "INP"
            self.save()


class StudentSubmission(Submission):
    member = models.ForeignKey(Member, null=False, on_delete=models.PROTECT)
    class Meta:
        app_label = 'submission'
    def get_userid(self):
        return self.member.person.userid
    def __str__(self):
        return "%s->%s@%s" % (self.member.person.userid, self.activity, self.created_at)
    def short_str(self):
        return "%s submission by %s at %s" % (self.activity.short_str(), self.member.person.userid, self.created_at.strftime("%Y-%m-%d %H:%M"))
    def creator_str(self):
        return self.member.person.full_email()
    def get_absolute_url(self):
        return reverse('offering:submission:show_student_submission_staff', kwargs={'course_slug': self.member.offering.slug, 'activity_slug': self.activity.slug, 'userid': self.member.person.userid})
    def file_slug(self):
        return self.member.person.userid_or_emplid()


class GroupSubmission(Submission):
    group = models.ForeignKey(Group, null=False, on_delete=models.PROTECT)
    creator = models.ForeignKey(Member, null=False, on_delete=models.PROTECT)

    class Meta:
        app_label = 'submission'
    def get_userid(self):
        return self.group.manager.person.userid
    def __str__(self):
        return "%s->%s@%s" % (self.group.manager.person.userid, self.activity, self.created_at)
    def short_str(self):
        return "%s submission by %s for group %s at %s" % (self.activity.short_str(), self.creator.person.userid, self.group.name, self.created_at.strftime("%Y-%m-%d %H:%M"))
    def creator_str(self):
        return self.group.name
    def get_absolute_url(self):
        return reverse('offering:submission:show_student_submission_staff', kwargs={'course_slug': self.group.courseoffering.slug, 'activity_slug': self.activity.slug, 'userid': self.creator.person.userid})
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
                        % (self.creator.person.name_pref(), self.activity.name),
                    url=reverse('offering:submission:show_components', kwargs={'course_slug': self.group.courseoffering.slug, 'activity_slug': member.activity.slug})
                    )
                n.save()


def submission_upload_path(instance, filename):
    return upload_path(instance.component.activity.offering.slug, filename)


class SubmittedComponent(models.Model):
    """
    Part of a student's/group's submission
    """
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT)
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
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")
    def __lt__(self, other):
        return other.submit_time < self.submit_time
    class Meta:
        ordering = ['submit_time']
        app_label = 'submission'
    def get_size_in_kb(self):
        res = int(self.get_size())/1024
        return res
    def get_submitter(self):
        group = GroupSubmission.objects.filter(id=self.submission.id)
        if len(group) == 0:
            student = StudentSubmission.objects.filter(id=self.submission.id)
            return student.member.person
        return group[0].creator.person
    def __str__(self):
        return "%s@%s" % (self.submission.activity, self.submission.created_at)
    def get_fieldfile(self) -> Optional[FieldFile]:
        # default implementation: subclasses should override and return the relevant FieldFile.
        return None

    def sendfile(self, upfile, response):
        """
        Send the contents of the file as the response, given a FileField object to read from.
        """
        path, filename = os.path.split(upfile.name)
        response['Content-Disposition'] = 'inline; filename="' + filename + '"'
        try:
            upfile.open('rb')
        except IOError:
            response['Content-type'] = "text/plain"
            response.write("File missing. It has likely been archived.")
            return

        for data in upfile:
            response.write(data)

    def file_filename(self, upfile, prefix=None):
        """
        Come up with a filename for the uploaded file in a ZIP archive.
        """
        filename = os.path.split(upfile.name)[1]
        if prefix:
            filename = os.path.join(prefix, filename)
        return filename

    def file_hash(self):
        """
        Create sha256 Hash of the submitted file contents, or None if this subclass doesn't contain a file
        """
        f = self.get_fieldfile()
        if f is None:
            return None

        try:
            fh = f.open('rb')
        except IOError:
            return None

        h = hashlib.sha256()
        for data in fh:
            h.update(data)
        return h


# adapted from http://stackoverflow.com/questions/849142/how-to-limit-the-maximum-value-of-a-numeric-field-in-a-django-model
class FileSizeField(models.PositiveIntegerField):
    def __init__(self, verbose_name=None, name=None, **kwargs):
        self.min_value, self.max_value = 0, settings.MAX_SUBMISSION_SIZE
        models.IntegerField.__init__(self, verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value':self.max_value}
        defaults.update(kwargs)
        field = super(FileSizeField, self).formfield(**defaults)
        # monkey-patch a better error message
        for v in field.validators:
            if isinstance(v, MaxValueValidator):
                v.message = "We currently limit submissions to %i kB on this system. For larger files, we suggest having students upload the files to their web space and submitting a URL." % (settings.MAX_SUBMISSION_SIZE)
        return field


GENERATOR_CHOICES = [ # first elements must be URL-safe slug-like things
    ('MOSS', 'MOSS'),
]


class SimilarityResult(models.Model):
    """
    Model class representing a set of similarity results for an activity.
    """
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    generator = models.CharField(max_length=4, null=False, blank=False, choices=GENERATOR_CHOICES, help_text='tool that generated the similarity results')
    created_at = models.DateTimeField(auto_now_add=True)
    config = JSONField(default=dict)

    class Meta:
        unique_together = [('activity', 'generator')]

    @classmethod
    def cleanup_old(cls, age=timedelta(days=30)):
        '''
        Old SimilarityResults will be deleted, but instructor can regenerate if they wish.
        '''
        cutoff = datetime.now() - age
        old = cls.objects.filter(created_at__lt=cutoff)
        old.delete()


def similarity_upload_path(instance, filename):
    return upload_path(instance.result.activity.offering.slug, '_similarity', filename)


class SimilarityData(models.Model):
    """
    Data for one submission/finding in a SimilarityResult.

    SimilarityData.file may be null if only the JSON data is being used.
    SimilarityData.label is used to identify in a way the generator understands.
    SimilarityData.submission may be set if we know the corresponding Submission instance.
    """
    result = models.ForeignKey(SimilarityResult, on_delete=models.CASCADE)
    label = models.CharField(max_length=100, null=False, blank=False, help_text='identifier used to find this file within the SimilarityResult')
    file = models.FileField(upload_to=similarity_upload_path, blank=True, null=True, max_length=500, storage=UploadedFileStorage)
    submission = models.ForeignKey(Submission, null=True, on_delete=models.CASCADE, related_name='+')
    config = JSONField(default=dict)

    class Meta:
        unique_together = [('result', 'label')]


# based on https://stackoverflow.com/a/16041527/6871666
@receiver(models.signals.post_delete, sender=SimilarityData)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem when corresponding SimilarityData object is deleted.
    """
    if instance.file:
        path = instance.file.path
        if os.path.isfile(path):
            os.remove(path)

        # also containing directory, if empty
        directory = os.path.split(path)[0]
        if os.path.isdir(directory):
            try:
                os.rmdir(directory)
            except OSError:
                pass
