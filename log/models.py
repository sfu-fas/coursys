from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class LogEntry(models.Model):
    """
    A record of activity within the system.  The "description" should be a reasonably-complete
    description of the activity that has occurred.  The "related_object" should be the object
    that was modified.
    
    self.userid == '' indicated action by non-logged-in user.
    
    Sample usage (e.g. editing a student's grade on an assignment)
        activity = NumericActivity.objects.get(...)
        student = Person.objects.get(...)
        grade = NumericGrade.objects.get(...)
        grade.value = new_grade
        grade.save()
        l = LogEntry(userid=request.user.username, 
              description="edited grade on %s for %s changed to %s" % (activity, student.userid, new_grade),
              related_object=grade )
        l.save()
    """
    userid = models.CharField(max_length=8, null=False, db_index=True,
        help_text='Userid who made the change')
    datetime = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, help_text="Description from the system of the change made")
    comment = models.TextField(null=True, help_text="Comment from the user (if available)")

    # link to object that was changed
    content_type = models.ForeignKey(ContentType, null=True, related_name="content_type", on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(null=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    class Meta:
        ordering = ['-datetime']

    def save(self, *args, **kwargs):
        # self.content_type might be null if the related item is deleted, but must be created with one.
        assert self.content_type
        if len(self.description) > 255:
            self.description = self.description[:252] + '...'
        return super().save(*args, **kwargs)

    def display(self):
        return "%s - %s - %s" % (self.userid, self.description, self.comment)

    __str__ = display

