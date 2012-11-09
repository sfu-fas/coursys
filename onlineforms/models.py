from django.db import models
from coredata.models import Person, Unit
from jsonfield import JSONField
 
# choices for Form.initiator field
INITIATOR_CHOICES = [
        ('LOG', 'Logged-in SFU users'),
        ('ANY', 'Anyone, including non-SFU users'),
        ('NON', 'Nobody: form cannot be filled out'),  # used to deactivate a form, or during creation/editing.
        # may add others if needed, e.g. instructors, admin staff, majors in a specific program, ...
        ]

# choices for the Sheet.can_view field
VIEWABLE_CHOICES = [
        ('ALL', 'Filler can see all info on previous sheets'),
        ('NON', "Filler can't see any info on other sheets (just name/email of initiator)"),
        ]

# choices for the Field.fieldtype field
FIELD_TYPE_CHOICES = [
        ('SMTX', 'Small Text (single line)'),
        ('MDTX', 'Medium Text (a few lines)'),
        ('LGTX', 'Large Text (many lines)'),
        ('EMAI', 'Email address'),
        ('RADI', 'Select with radio buttons'),
        ('SEL1', 'Select with a drop-down menu'),
        ('SELN', 'Select multiple values'),
        ('LIST', 'Enter a list of short responses'),
        ('FILE', 'Upload a file'),
        ('URL', 'A web page address (URL)'),
        ('TEXT', 'An explanation block (user enters nothing)'),
        ('DIVI', 'A divider'),
        #('DATE', 'A date'),
        #('SEM', 'Semester'),
        # more may be added.
        ]

# mapping of field types to FieldType objects that implement their logic
from onlineforms.fieldtypes import *
FIELD_TYPE_MODELS = {
        'SMTX': SmallTextField,
        'MDTX': MediumTextField,
        }

class NonSFUFormFiller(models.Model):
    """
    A person without an SFU account that can fill out forms.
    """
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    email_address = models.EmailField(max_length=254)

    def __unicode__(self):
        return "%s, %s" % (self.last_name, self.first_name)
    def name(self):
        return "%s %s" % (self.first_name, self.last_name)
    def sortname(self):
        return "%s, %s" % (self.last_name, self.first_name)
    def initials(self):
        return "%s%s" % (self.first_name[0], self.last_name[0])
    def full_email(self):
        return "%s <%s>" % (self.name(), self.email())
    def email(self):
        return self.email_address

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    
    def email_mailto(self):
        "A mailto: URL for this person's email address: handles the case where we don't know an email for them."
        email = self.email()
        if email:
            return mark_safe('<a href="mailto:%s">%s</a>' % (escape(email), escape(email)))
        else:
            return "None"

class FormFiller(models.Model):
    """
    A wrapper class for filling forms. Is either a SFU account(Person) or a nonSFUFormFiller.
    """
    sfuFormFiller = models.ForeignKey(Person, null=True)
    nonSFUFormFiller = models.ForeignKey(NonSFUFormFiller, null=True)

    def getFormFiller(self):
        if self.sfuFormFiller != None:
            return self.sfuFormFiller
        elif self.nonSFUFormFiller != None:
            return self.nonSFUFormFiller
        else:
            raise Exception, "This form filler object is in an invalid state."

    def __unicode__(self):
        formFiller = self.getFormFiller()
        return formFiller.__unicode__()
    def name(self):
        formFiller = self.getFormFiller()
        return formFiller.name()
    def sortname(self):
        formFiller = self.getFormFiller()
        return formFiller.sortname()
    def initials(self):
        formFiller = self.getFormFiller()
        return formFiller.initials()
    def full_email(self):
        formFiller = self.getFormFiller()
        return formFiller.full_email()
    def email(self):
        formFiller = self.getFormFiller()
        return formFiller.email()

    def delete(self, *args, **kwargs):
        formFiller = self.getFormFiller()
        return formFiller.delete(*args, **kwargs)
    
    def email_mailto(self):
        formFiller = self.getFormFiller()
        return formFiller.email_mailto()

class FormGroup(models.Model):
    """
    A group that owns forms and form submissions.
    """
    unit = models.ForeignKey(Unit)
    name = models.CharField(max_length=60, null=False, blank=False)
    members = models.ManyToManyField(Person)

    class Meta:
        unique_together = (("unit", "name"),)

    def __unicode__(self):
        return "%s, %s" % (self.name, self.unit.label)

class Form(models.Model):
    title = models.CharField(max_length=60, null=False, blank=False)
    owner = models.ForeignKey(FormGroup)
    initiators = models.CharField(max_length=3, choices=INITIATOR_CHOICES, default="ANY")
    unit = models.ForeignKey(Unit)
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

class Sheet(models.Model):
    title = models.CharField(max_length=60, null=False, blank=False)
    form = models.ForeignKey(Form)
    # not sure if this should be not null, but if it is not null, what do we set as the initial
    # value since this field should be unique within the form?
    order = models.PositiveIntegerField(null=True, blank=True)
    # since it seems this is tied to order == 0, we could probably exchance with a method
    is_initial = models.BooleanField(default=False)
    can_view = models.CharField(max_length=4, choices=VIEWABLE_CHOICES, default="NON")
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('form', 'order'),)

class Field(models.Model):
    label = models.CharField(max_length=60, null=False, blank=False)
    sheet = models.ForeignKey(Sheet)
    # same question as above
    order = models.PositiveIntegerField(null=True, blank=True)
    required = models.BooleanField(default=True)
    fieldtype = models.CharField(max_length=4, choices=FIELD_TYPE_CHOICES, default="SMTX")
    config = JSONField(null=False, blank=False, default={}) # configuration as required by the fieldtype
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

