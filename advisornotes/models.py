from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from autoslug import AutoSlugField
from coredata.models import Person, Unit
from jsonfield import JSONField
from courselib.json_fields import getter_setter
from courselib.slugs import make_slug
import datetime, os.path

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
    notes = models.TextField(help_text="Any notes about the student", blank=True)
    unit = models.ForeignKey(Unit, help_text='The potential academic unit for the student', null=True, blank=True)
    def autoslug(self):
        return make_slug(self.first_name + ' ' + self.last_name)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
    
    def __unicode__(self):
        return "%s, %s" % (self.last_name, self.first_name)
    
    def name(self):
        return "%s %s" % (self.first_name, self.last_name)

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
    created_at = models.DateTimeField(auto_now_add=True)
    file_attachment = models.FileField(storage=NoteSystemStorage, null=True, 
                      upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200, editable = False)
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this note')
    # Set this flag if the note is no longer to be accessible.
    hidden = models.BooleanField(null=False, db_index=True, default=False)

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

