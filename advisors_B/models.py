from django.db import models

from django.template.defaultfilters import slugify

from timezones.fields import TimeZoneField

class Person(models.Model):
    """
    A person in the system (students, instuctors, etc.).
    """
    empid = models.PositiveIntegerField(db_index=True, unique=True, null=False,
        help_text='Employee ID (i.e. student number)')
    userid = models.CharField(max_length=8, null=True, db_index=True, unique=True,
        help_text='SFU Unix userid (i.e. part of SFU email address before the "@").')
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True)
    pref_first_name = models.CharField(max_length=32)
    
    def __unicode__(self):
        return "%s, %s" % (self.last_name, self.first_name)
    def name(self):
        return "%s %s" % (self.pref_first_name, self.last_name)
    def email(self):
        return "%s@sfu.ca" % (self.userid)
    class Meta:
        verbose_name_plural = "People"
        ordering = ['last_name', 'first_name', 'userid']

class OtherUser(models.Model):
    """
    Additional users of the system (not course-related).
    """
    ROLE_CHOICES = (
        ('ADVS', 'Advisor'),
        ('ADMN', 'Departmental Administrator'),
    )
    ROLES = dict(ROLE_CHOICES)
    person = models.ForeignKey(Person)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES)

    def __unicode__(self):
        return "%s (%s)" % (self.person, self.ROLES[str(self.role)])
    class Meta:
        unique_together = (('person', 'role'),)


class Note(models.Model):
    """
    A Note in the system (with particular student, creation date and author)
    """
    Content = models.CharField(max_length = 1000)
    Student = models.ForeignKey(Person)
    CreateDate = models.DateTimeField('create date')
    Author = models.ForeignKey(OtherUser)
    #file attachment
    Hidden = models.BooleanField(default = False)


    def __unicode__(self):
        return "%s , %s " % (str(self.CreateDate) , str(self.Student))

    def AssignDate(self):
        self.CreateDate = datetime.date.today()
        return





