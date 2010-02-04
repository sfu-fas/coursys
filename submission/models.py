from django.db import models
from grades.models import Activity
from coredata.models import Member
from groups.models import Group

STATUS_CHOICES = [
    ('NEW', 'New'),
    ('INP', 'In-Progress'),
    ('DON', 'Marked') ]

# per-activity models, defined by instructor:

class SubmissionComponent(models.Model):
    """
    A component of the activity that will be submitted by students
    """
    activity = models.ForeignKey(Activity)
    title = models.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")')
    position = models.PositiveSmallIntegerField()

class URLComponent(SubmissionComponent):
    "A URL submission component"
class ArchiveComponent(SubmissionComponent):
    "An archive file (TGZ/ZIP/RAR) submission component"
    max_size = models.PositiveIntegerField()

# per-submission models, created when a student/group submits an assignment:

class Submission(models.Model):
    """
    A student's or group's submission for an activity
    """
    activity = models.ForeignKey(Activity)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(Member, null=True)
    status = models.CharField(max_length=3, null=False, choices=STATUS_CHOICES)

class StudentSubmission(Submission):
    member = models.ForeignKey(Member, null=False)
class GroupSubmission(Submission):
    group = models.ForeignKey(Group, null=False)

# parts of a submission, created as part of a student/group submission

class SubmittedComponent(models.Model):
    """
    Part of a student's/group's submission
    """
    submission = models.ForeignKey(Submission)

class SubmittedURL(SubmittedComponent):
    component = models.ForeignKey(URLComponent, null=False)
    url = models.URLField(verify_exists=True)
class SubmittedArchive(SubmittedComponent):
    component = models.ForeignKey(ArchiveComponent, null=False)
    archive = models.FileField(upload_to="submittedarchive") # TODO: change to a more secure directory

