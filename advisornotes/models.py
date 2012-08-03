from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from autoslug import AutoSlugField
from coredata.models import Person, Unit, Course, CourseOffering
from jsonfield import JSONField
from courselib.slugs import make_slug
import datetime
from datetime import date
import os.path

NoteSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)


def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """
    fullpath = os.path.join(
            'advisornotes',
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.advisor.userid),
            filename.encode('ascii', 'ignore'))
    return fullpath


class NonStudent(models.Model):
    """
    For a person (propspective student) who isn't part of the university
    """
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    pref_first_name = models.CharField(max_length=32, null=True, blank=True)
    high_school = models.CharField(max_length=32, null=True, blank=True)
    college = models.CharField(max_length=32, null=True, blank=True)
    start_year = models.IntegerField(null=True, blank=True, help_text="The predicted/potential start year")
    notes = models.TextField(help_text="Any general information for the student", blank=True)
    unit = models.ForeignKey(Unit, help_text='The potential academic unit for the student', null=True, blank=True)

    def autoslug(self):
        return make_slug(self.first_name + ' ' + self.last_name)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:

    def __unicode__(self):
        return "%s, %s" % (self.last_name, self.first_name)

    def name(self):
        return "%s %s" % (self.first_name, self.last_name)
    def sortname(self):
        return "%s, %s" % (self.last_name, self.first_name)

    def search_label_value(self):
        return "%s (Prospective)" % (self.name())

    def __hash__(self):
        return (self.first_name, self.middle_name, self.last_name, self.pref_first_name, self.high_school).__hash__()


class AdvisorNote(models.Model):
    """
    An academic advisor's note about a student.
    """
    text = models.TextField(blank=False, null=False, verbose_name="Contents",
                            help_text='Note about a student')
    student = models.ForeignKey(Person, related_name='student',
                                help_text='The student that the note is about',
                                editable=False, null=True)
    nonstudent = models.ForeignKey(NonStudent, editable=False, null=True,
                                help_text='The non-student that the note is about')
    advisor = models.ForeignKey(Person, related_name='advisor',
                                help_text='The advisor that created the note',
                                editable=False)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    file_attachment = models.FileField(storage=NoteSystemStorage, null=True,
                      upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200, editable=False)
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this note')
    # Set this flag if the note is no longer to be accessible.
    hidden = models.BooleanField(null=False, db_index=True, default=False)
    emailed = models.BooleanField(null=False, default=False)

    def __unicode__(self):
        return unicode(self.student) + "@" + unicode(self.created_at)

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted, set the hidden flag instead."

    class Meta:
        ordering = ['student', 'created_at']

    def save(self, *args, **kwargs):
        # make sure one of student and nonstudent is there
        if not self.student and not self.nonstudent:
            raise ValueError, "AdvisorNote must have either student or non-student specified."
        super(AdvisorNote, self).save(*args, **kwargs)

    def attachment_filename(self):
        """
        Return the filename only (no path) for the attachment.
        """
        _, filename = os.path.split(self.file_attachment.name)
        return filename

    def __hash__(self):
        return (self.text, self.created_at, self.file_attachment).__hash__()


ARTIFACT_CATEGORIES = (
    ("INS", "Institution"),
    ("PRO", "Program"),
    ("OTH", "Other"),
)


class Artifact(models.Model):
    name = models.CharField(max_length=140, help_text='The name of the artifact', null=False, blank=False)
    category = models.CharField(max_length=3, choices=ARTIFACT_CATEGORIES, null=False, blank=False)

    def autoslug(self):
        return make_slug(self.unit.label + '-' + self.name)

    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this artifact', null=False, blank=False)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'unit')]

    def __unicode__(self):
        return unicode(self.name) + ' (' + unicode(self.get_category_display()) + ')'


NOTE_STATUSES = (
    ("IMP", "Important"),
)

NOTE_CATEGORIES = (
    ("EXC", "Exceptions"),
    ("WAI", "Waivers"),
    ("REQ", "Requirements"),
    ("TRA", "Transfers"),
    ("MIS", "Miscellaneous")
)


class ArtifactNote(models.Model):
    course = models.ForeignKey(Course, help_text='The course that the note is about', null=True, blank=True)
    course_offering = models.ForeignKey(CourseOffering, help_text='The course offering that the note is about', null=True, blank=True)
    artifact = models.ForeignKey(Artifact, help_text='The artifact that the note is about', null=True, blank=True)
    important = models.BooleanField()
    category = models.CharField(max_length=3, choices=NOTE_CATEGORIES)
    text = models.TextField(blank=False, null=False, verbose_name="Contents",
                            help_text='Note about a student')
    advisor = models.ForeignKey(Person, help_text='The advisor that created the note', editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    best_before = models.DateField(help_text='The effective date for this note', null=True, blank=True)
    file_attachment = models.FileField(storage=NoteSystemStorage, null=True,
                      upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200, editable=False)
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this note')
    # Set this flag if the note is no longer to be accessible.
    hidden = models.BooleanField(null=False, db_index=True, default=False)

    def __unicode__(self):
        if self.course:
            return unicode(self.course) + "@" + unicode(self.created_at)
        elif self.course_offering:
            return unicode(self.course_offering) + "@" + unicode(self.created_at)
        else:
            return unicode(self.artifact) + "@" + unicode(self.created_at)

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted, set the hidden flag instead."

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        # make sure one of course, course_offering or artifact is there
        if not self.course and not self.course_offering and not self.artifact:
            raise ValueError, "Artifact note must have either course, course offering or artifact specified."

        # make sure only one course, course_offering or artifact is related
        if (self.course and self.course_offering) or (self.course and self.artifact) or (self.course_offering and self.artifact):
            raise ValueError, "Artifact cannot have more than one related course, course offering or artifact."
        super(ArtifactNote, self).save(*args, **kwargs)

    def attachment_filename(self):
        """
        Return the filename only (no path) for the attachment.
        """
        _, filename = os.path.split(self.file_attachment.name)
        return filename

    def __hash__(self):
        return (self.text, self.created_at, self.file_attachment).__hash__()

    def is_expired(self):
        return date.today() > self.best_before

PROBLEM_STATUSES = (
    ("OPEN", "New"),
    ("PEND", "Pending action"),
    ("RESO", "Resolved"),
    ("IGNR", "Ignored"),
    ("CONT", "Contacted"),
    ("DUPL", "Duplicate"),
)
OPEN_STATUSES = ("OPEN", "PEND")
CLOSED_STATUSES = ("RESO", "IGNR", "CONT", "DUPL")

class Problem(models.Model):
    """
    A problem code associated with a student from API
    """
    person = models.ForeignKey(Person)
    code = models.CharField(help_text="The problem code (ex. GPA < 2.4)", max_length=30)
    description = models.CharField(help_text="Short description of the problem", max_length=80)
    comments = models.TextField(help_text="Longer details of problem", null=True, blank=True)
    status = models.CharField(max_length=4, choices=PROBLEM_STATUSES, null=False, blank=False, default="OPEN")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True)
    resolution_lasts = models.IntegerField(help_text="Default number of days resolution should last, sent by API", null=False)
    resolved_until = models.DateField(null=True, blank=True, help_text="If resolved, til when should this resolution last?")
    unit = models.ForeignKey(Unit, null=False)
    
    def is_closed(self):
        return self.status in CLOSED_STATUSES
    
    def has_resolution_expired(self):
        return datetime.date.today() > self.resolved_until
    
    def default_resolved_until(self):
        period = datetime.timedelta(days=self.resolution_lasts)
        return datetime.datetime.now() + period
    
    def save(self, *args, **kwargs):
        if self.is_closed() and not self.resolved_until:
            self.resolved_until = self.default_resolved_until()
        if self.is_closed() and not self.resolved_at:
            self.resolved_at = datetime.datetime.now()
        super(Problem, self).save(*args, **kwargs)

# Incoming Problem logic:
# 1. No matching code/student/unit: add.
# 2. Matching code/student/unit, resolved_until >= now: drop.
# 3. Matching code/student/unit, not resolved: update all fields from API (not created_at).
# 4. Matching code/student/unit, resolved_unil < now: add.


