from django.db import models
from grades.models import Activity
from coredata.models import Member
from groups.models import Group

STATUS_CHOICES = [
    ('NEW', 'New'),
    ('INP', 'In-Progress'),
    ('DON', 'Marked') ]

TYPE_CHOICES = [
    ('Archive', 'Archive Component'),
    ('URL', 'URL Component'),
    ('C/C++', 'C/C++ Component'),
    ('Plain', 'Plain Text Component'),
]

# per-activity models, defined by instructor:

class SubmissionComponent(models.Model):
    """
    A component of the activity that will be submitted by students
    """
    activity = models.ForeignKey(Activity)
    title = models.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")')
    position = models.PositiveSmallIntegerField()

    def __cmp__(self, other):
        return cmp(self.position, other.position)
    class Meta:
        ordering = ['position']

class URLComponent(SubmissionComponent):
    "A URL submission component"
class ArchiveComponent(SubmissionComponent):
    "An archive file (TGZ/ZIP/RAR) submission component"
    max_size = models.PositiveIntegerField()
class CppComponent(SubmissionComponent):
    "C/C++ file submission component"
class PlainTextComponent(SubmissionComponent):
    "Text file submission component"

# list of all subclasses of SubmissionComponent:
# MUST have deepest subclasses first (i.e. nothing *after* a class is one of its subclasses)
COMPONENT_TYPES = [URLComponent, ArchiveComponent, CppComponent, PlainTextComponent]

def AllComponents(activity):
    """
    Return all components for this activity as their most specific class.
    """
    components = [] # list of components
    found = set() # keep track of what has been found so we can exclude less-specific duplicates.
    for ComponentType in COMPONENT_TYPES:
        comps = list(ComponentType.objects.filter(activity=activity))
        components.extend( (c for c in comps if c.id not in found) )
        found.update( (c.id for c in comps) )

    components.sort()
    return components



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
class SubmittedCpp(SubmittedComponent):
    component = models.ForeignKey(CppComponent, null=False)
    cpp = models.FileField(upload_to="submittedcpp") # TODO: change to a more secure directory
class SubmittedPlainText(SubmittedComponent):
    component = models.ForeignKey(CppComponent, null=False)
    text = models.CharField(max_length=3000)
