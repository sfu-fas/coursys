from django.db import models
from autoslug import AutoSlugField
from coredata.models import Person, Unit, Course, CourseOffering, GENDER_DESCR
from courselib.json_fields import JSONField, config_property
from courselib.slugs import make_slug
from courselib.storage import UploadedFileStorage, upload_path
from courselib.markup import markup_to_html
from datetime import date
import datetime
import os.path


# Used to determine if you have any non-end-dated visit, but only of the newer type, with end-dates added by a view.
# All the older visits will not have an end-date.
ADVISOR_VISIT_VERSION = 1

ADVISING_CAMPUS_CHOICES = (
        ('BRNBY', 'Burnaby'),
        ('SURRY', 'Surrey'),
        ('VANCR', 'Vancouver'),
        )


def attachment_upload_to(instance, filename):
    return upload_path('advisornotes', filename)

class Announcement(models.Model):
    title = models.CharField(max_length=100)
    message = models.TextField(blank=False, null=False)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    author = models.ForeignKey(Person, related_name='posted_by', on_delete=models.PROTECT,
                                help_text='The user who created the news item',
                                editable=False)
    hidden = models.BooleanField(null=False, db_index=True, default=False)
    unit = models.ForeignKey(Unit, help_text='Academic unit who owns the note', null=False, blank=False,
                             on_delete=models.PROTECT)

    config = JSONField(null=False, blank=False, default=dict)

    markup = config_property('markup', 'plain')
    math = config_property('math', False)

    def __str__(self):
        return "%s" % (self.title)

    class Meta:
       ordering = ('-created_at',)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted, set the hidden flag instead.")
    
    def html_content(self):
        return markup_to_html(self.message, self.markup, restricted=False)

class NonStudent(models.Model):
    """
    For a person (prospective student) who isn't part of the university
    """
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    pref_first_name = models.CharField(max_length=32, null=True, blank=True)
    email_address = models.EmailField(null=True, blank=True, help_text="Needed only if you want to copy the student on notes")
    high_school = models.CharField(max_length=32, null=True, blank=True)
    college = models.CharField(max_length=32, null=True, blank=True)
    start_year = models.IntegerField(null=True, blank=True, help_text="The predicted/potential start year")
    notes = models.TextField(help_text="Any general information for the student", blank=True)
    unit = models.ForeignKey(Unit, help_text='The potential academic unit for the student', null=True, blank=True, on_delete=models.PROTECT)

    def autoslug(self):
        return make_slug(self.first_name + ' ' + self.last_name)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    def __str__(self):
        return "%s, %s" % (self.last_name, self.first_name)

    def name(self):
        return "%s %s" % (self.first_name, self.last_name)
    def sortname(self):
        return "%s, %s" % (self.last_name, self.first_name)

    def search_label_value(self):
        return "%s (Prospective %s)" % (self.name(), self.start_year)

    def unique_tuple(self):
        return (self.first_name, self.middle_name, self.last_name, self.pref_first_name, self.high_school)

    def __hash__(self):
        return self.unique_tuple().__hash__()

    def email(self):
        return self.email_address

class AdvisorNote(models.Model):
    """
    An academic advisor's note about a student.
    """
    text = models.TextField(blank=False, null=False, verbose_name="Contents",
                            help_text='Note about a student')
    student = models.ForeignKey(Person, related_name='student', on_delete=models.PROTECT,
                                help_text='The student that the note is about',
                                editable=False, null=True)
    nonstudent = models.ForeignKey(NonStudent, editable=False, null=True, on_delete=models.PROTECT,
                                help_text='The non-student that the note is about')
    advisor = models.ForeignKey(Person, related_name='advisor', on_delete=models.PROTECT,
                                help_text='The advisor that created the note',
                                editable=False)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    file_attachment = models.FileField(storage=UploadedFileStorage, null=True,
                      upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200, editable=False)
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this note', on_delete=models.PROTECT)
    # Set this flag if the note is no longer to be accessible.
    hidden = models.BooleanField(null=False, db_index=True, default=False)
    emailed = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    # 'markup': markup language used in reminder content: see courselib/markup.py
    # 'math': page uses MathJax? (boolean)
    markup = config_property('markup', 'plain')
    math = config_property('math', False)

    def __str__(self):
        return str(self.student) + "@" + str(self.created_at)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted, set the hidden flag instead.")

    class Meta:
        ordering = ['student', 'created_at']

    def save(self, *args, **kwargs):
        # make sure one of student and nonstudent is there
        if not self.student and not self.nonstudent:
            raise ValueError("AdvisorNote must have either student or non-student specified.")
        super(AdvisorNote, self).save(*args, **kwargs)

    def attachment_filename(self):
        """
        Return the filename only (no path) for the attachment.
        """
        _, filename = os.path.split(self.file_attachment.name)
        return filename
    
    def unique_tuple(self):
        return ( make_slug(self.text[0:100]), self.created_at.isoformat() )
    
    def __hash__(self):
        return self.unique_tuple().__hash__()

    def html_content(self):
        return markup_to_html(self.text, self.markup, restricted=False)

ARTIFACT_CATEGORIES = (
    ("INS", "Institution"),
    ("PRO", "Program"),
    ("OTH", "Other"),
)


class Artifact(models.Model):
    name = models.CharField(max_length=140, help_text='The name of the artifact', null=False, blank=False)
    category = models.CharField(max_length=3, choices=ARTIFACT_CATEGORIES, null=False, blank=False)
    # flag if artifact is retired
    hidden = models.BooleanField(null=False, default=False)

    def autoslug(self):
        return make_slug(self.unit.label + '-' + self.name)

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this artifact', null=False, blank=False, on_delete=models.PROTECT)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'unit')]

    def __str__(self):
        return str(self.name) + ' (' + str(self.get_category_display()) + ')'


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
    course = models.ForeignKey(Course, help_text='The course that the note is about', null=True, blank=True, on_delete=models.PROTECT)
    course_offering = models.ForeignKey(CourseOffering, help_text='The course offering that the note is about', null=True, blank=True, on_delete=models.PROTECT)
    artifact = models.ForeignKey(Artifact, help_text='The artifact that the note is about', null=True, blank=True, on_delete=models.PROTECT)
    important = models.BooleanField(default=False)
    category = models.CharField(max_length=3, choices=NOTE_CATEGORIES)
    text = models.TextField(blank=False, null=False, verbose_name="Contents",
                            help_text='Note about a student')
    advisor = models.ForeignKey(Person, help_text='The advisor that created the note', editable=False, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    best_before = models.DateField(help_text='The effective date for this note', null=True, blank=True)
    file_attachment = models.FileField(storage=UploadedFileStorage, null=True,
                      upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200, editable=False)
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this note', on_delete=models.PROTECT)
    # Set this flag if the note is no longer to be accessible.
    hidden = models.BooleanField(null=False, db_index=True, default=False)

    def __str__(self):
        if self.course:
            return str(self.course) + "@" + str(self.created_at)
        elif self.course_offering:
            return str(self.course_offering) + "@" + str(self.created_at)
        else:
            return str(self.artifact) + "@" + str(self.created_at)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted, set the hidden flag instead.")

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        # make sure one of course, course_offering or artifact is there
        if not self.course and not self.course_offering and not self.artifact:
            raise ValueError("Artifact note must have either course, course offering or artifact specified.")

        # make sure only one course, course_offering or artifact is related
        if (self.course and self.course_offering) or (self.course and self.artifact) or (self.course_offering and self.artifact):
            raise ValueError("Artifact cannot have more than one related course, course offering or artifact.")
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
        return self.best_before and date.today() > self.best_before


class AdvisorVisitCategoryQuerySet(models.QuerySet):
    """
    As usual, define some querysets.
    """

    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=units)


class AdvisorVisitCategory(models.Model):
    """
    Allow each unit to manage the categories which are now included in a visit.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT)
    label = models.CharField(null=False, blank=False, max_length=50)
    description = models.CharField(null=True, blank=True, max_length=500)
    hidden = models.BooleanField(null=False, blank=False, default=False, editable=False)
    config = JSONField(null=False, blank=False, default=dict, editable=False)  # addition configuration stuff:

    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.label)

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __str__(self):
        return self.label

    objects = AdvisorVisitCategoryQuerySet.as_manager()

    def delete(self):
        # As usual, only hide stuff, don't delete it.
        self.hidden = True
        self.save()


class AdvisorVisitQuerySet(models.QuerySet):
    """
    As usual, define some querysets.
    """

    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=Unit.sub_units(units))


class AdvisorVisit(models.Model):
    """
    Record of a visit to an advisor.

    We expect to record at least one of (1) the student/nonstudent, or (2) the unit where the student's program lives.
    The idea is that advisors can go to the student advising record and click "visited", or more generically click "a
    CMPT student visited".

    Only (1) is implemented in the frontend for now.

    Update:  They don't seem to really want (2), so that's mainly unreachable right now.
    """
    student = models.ForeignKey(Person, help_text='The student that visited the advisor', on_delete=models.PROTECT,
                                blank=True, null=True, related_name='+')
    nonstudent = models.ForeignKey(NonStudent, blank=True, null=True, on_delete=models.PROTECT,
                                   help_text='The non-student that visited')
    program = models.ForeignKey(Unit, help_text='The unit of the program the student is in', blank=True, null=True,
                                on_delete=models.PROTECT,
                                related_name='+')
    advisor = models.ForeignKey(Person, help_text='The advisor that created the note', on_delete=models.PROTECT,
                                editable=False, related_name='+')

    created_at = models.DateTimeField(default=datetime.datetime.now)
    end_time = models.DateTimeField(null=True, blank=True)
    campus = models.CharField(null=False, blank=False, choices=ADVISING_CAMPUS_CHOICES, max_length=5)
    categories = models.ManyToManyField(AdvisorVisitCategory, blank=True)
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this visit', null=False,
                             on_delete=models.PROTECT)
    version = models.PositiveSmallIntegerField(null=False, blank=False, default=0, editable=False)
    hidden = models.BooleanField(null=False, blank=False, default=False, editable=False)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    programs = config_property('programs', '')
    cgpa = config_property('cgpa', '')
    credits = config_property('credits', '')
    gender = config_property('gender', '')
    citizenship = config_property('citizenship', '')

    objects = AdvisorVisitQuerySet.as_manager()

    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.get_userid() + '-' + self.advisor.userid)

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def save(self, *args, **kwargs):
        # ensure we always have either the student, nonstudent, or program unit.
        assert self.student or self.nonstudent or self.program
        assert not (self.student and self.nonstudent)
        super(AdvisorVisit, self).save(*args, **kwargs)

    # Template display helper methods
    def categories_display(self):
        return '; '.join(c.label for c in self.categories.all())

    def has_categories(self):
        return self.categories.all().count() > 0

    def get_userid(self):
        if self.student:
            return self.student.userid_or_emplid()
        else:
            return self.nonstudent.slug or 'none'

    def get_full_name(self):
        if self.student:
            return self.student.name()
        else:
            return self.nonstudent.name()

    def get_duration(self):
        if self.end_time:
            return str(self.end_time - self.created_at).split('.')[0]
        else:
            return None

    def has_sims_data(self):
        return self.programs or self.cgpa or self.credits or self.gender or self.citizenship

    def get_email(self):
        if self.student:
            return self.student.email()
        else:
            return self.nonstudent.email()

    def get_gender_display(self):
        GENDER_DESCR.get(self.gender, 'unknown')

    def get_created_at_display(self):
        return self.created_at.strftime("%Y/%m/%d %H:%M")

    def get_end_time_display(self):
        if self.end_time:
            return self.end_time.strftime("%Y/%m/%d %H:%M")
        else:
            return ''
