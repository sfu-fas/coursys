from django.db import models
from coredata.models import Person, Unit
from datetime import datetime
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os.path, decimal

NoteSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped 
    """
    fullpath = os.path.join(
            'advisornotes',
            datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.advisor.userid),
            filename.encode('ascii', 'ignore'))
    return fullpath 

class AdvisorNote(models.Model):
    """
    An academic advisor's note about a student. 
    """
    text = models.TextField(blank=False, null=False, verbose_name="Contents of note.",
                            help_text='Enter a note about a student')
    student = models.ForeignKey(Person, related_name='student',
                                help_text='The student that the note is about.',
                                editable = False)
    advisor = models.ForeignKey(Person, related_name='advisor',
                                help_text='The advisor that created the note.',
                                editable = False)
    created_at = models.DateTimeField(auto_now_add=True)
    file_attachment = models.FileField(storage=NoteSystemStorage, null = True, 
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
    def attachment_filename(self):
        """
        Return the filename only (no path) for the attachment.
        """
        path, filename = os.path.split(self.file_attachment.name)
        return filename

