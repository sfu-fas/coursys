import os
from django.db import models, transaction
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape
from coredata.models import Person, Unit
from jsonfield import JSONField
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from django.db.models import Max
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import datetime, random, sha

# choices for Form.initiator field
from onlineforms.fieldtypes.other import FileCustomField, DividerField, URLCustomField, ListField
from onlineforms.fieldtypes.select import DropdownSelectField, RadioSelectField, MultipleSelectField
from onlineforms.fieldtypes.text import LargeTextField, ExplanationTextField, EmailTextField

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
#from onlineforms.fieldtypes.other import DividerField
FIELD_TYPE_MODELS = {
        'SMTX': SmallTextField,
        'MDTX': MediumTextField,
        'LGTX': LargeTextField,
        'EMAI': EmailTextField,
        'RADI': RadioSelectField,
        'SEL1': DropdownSelectField,
        'SELN': MultipleSelectField,
        'LIST': ListField,
        'FILE': FileCustomField,
        'URL': URLCustomField,
        'TEXT': ExplanationTextField,
        'DIVI': DividerField,
        }

# mapping of different statuses the forms can be in
SUBMISSION_STATUS = [
        ('WAIT', "Waiting for the owner to send it to someone else or change status to \"done\""),
        ('DONE', "No further action required"),
        ]
        
FORM_SUBMISSION_STATUS = [('PEND', "The document is still being worked on")] + SUBMISSION_STATUS

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
    def autoslug(self):
        return make_slug(self.unit.label + ' ' + self.name)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

    class Meta:
        unique_together = (("unit", "name"),)

    def __unicode__(self):
        return "%s, %s" % (self.name, self.unit.label)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."

class _FormCoherenceMixin(object):
    """
    Class to mix-in to maintain the .active and .original fields
    properly when saving form objects.
    """
    def clone(self):
        """
        Return a cloned copy of self, which has *not* been saved.
        """
        # from http://stackoverflow.com/a/4733702
        new_kwargs = dict([(fld.name, getattr(self, fld.name)) 
                           for fld in self._meta.fields if fld.name != self._meta.pk.name])
        return self.__class__(**new_kwargs)

    def cleanup_fields(self):
        """
        Called after self.save() to manage the .active and .original fields
        """
        # There can be only one [active instance of this Form/Sheet/Field].
        if self.active and self.original:
            others = type(self).objects.filter(original=self.original) \
                                 .exclude(id=self.id)
            
            # only de-activate siblings, not cousins.
            # i.e. other related sheets/fields in *other* versions of the form should still be active
            if isinstance(self, Sheet):
                others = others.filter(form=self.form)
            elif isinstance(self, Field):
                others = others.filter(sheet=self.sheet)
            
            others.update(active=False)

        # ensure self.original is populated: should already be set to
        # oldinstance.original when copying.
        if not self.original:
            assert self.id # infinite loop if called before self is saved (and thus gets an id)
            self.original = self
            self.save()


class Form(models.Model, _FormCoherenceMixin):
    title = models.CharField(max_length=60, null=False, blank=False)
    owner = models.ForeignKey(FormGroup)
    description = models.CharField(max_length=500, null=False, blank=False)
    initiators = models.CharField(max_length=3, choices=INITIATOR_CHOICES, default="NON")
    unit = models.ForeignKey(Unit)
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def autoslug(self):
        return make_slug(self.unit.label + ' ' + self.title)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

    def __unicode__(self):
        return "%s [%s]" % (self.title, self.id)
    
    def delete(self, *args, **kwargs):
        self.active = False
        self.save()

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        instance = super(Form, self).save(*args, **kwargs)
        self.cleanup_fields()
        return instance
    
    @property
    def initial_sheet(self):
        sheets = Sheet.objects.filter(form=self, active=True, is_initial=True)
        if len(sheets) > 0:
            return sheets[0]
        else:
            return None

    cached_sheets = None
    def get_sheets(self, refetch=False):
        if refetch or not(self.cached_sheets):
            self.cached_sheets = Sheet.objects.filter(form=self, active=True).order_by('order')
        return self.cached_sheets
    sheets = property(get_sheets)

class Sheet(models.Model, _FormCoherenceMixin):
    title = models.CharField(max_length=60, null=False, blank=False)
    # the form this sheet is a part of
    form = models.ForeignKey(Form)
    # specifies the order within a form
    order = models.PositiveIntegerField()
    # Flag to indicate whether this is the first sheet in the form
    is_initial = models.BooleanField(default=False)
    # indicates whether a person filling a sheet can see the results from all the previous sheets
    can_view = models.CharField(max_length=4, choices=VIEWABLE_CHOICES, default="NON")
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    def autoslug(self):
        return make_slug(self.title)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='form')

    #class Meta:
    #    unique_together = (('form', 'order'),)

    def __unicode__(self):
        return "%s, %s [%i]" % (self.form, self.title, self.id)

    def delete(self, *args, **kwargs):
        if self.is_initial == True:
            raise NotImplementedError
        else:
            self.active = False
            self.save()

    @transaction.commit_on_success
    def safe_save(self):
        """
        Save a copy of this sheet, and return the copy: does not modify self.
        """
        # clone the sheet
        sheet2 = self.clone()
        sheet2.save()
        sheet2.cleanup_fields()
        # copy the fields
        for field1 in Field.objects.filter(sheet=self, active=True):
            field2 = field1.clone()
            field2.sheet = sheet2
            field2.save()
        return sheet2       

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        # if this sheet is just being created it needs a order number
        if(self.order == None):
            max_aggregate = Sheet.objects.filter(form=self.form).aggregate(Max('order'))
            if(max_aggregate['order__max'] == None):
                next_order = 0
            else:
                next_order = max_aggregate['order__max'] + 1
            self.order = next_order

        #assert (self.is_initial and self.order==0) or (not self.is_initial and self.order>0)
  
        super(Sheet, self).save(*args, **kwargs)
        self.cleanup_fields()

     

    cached_fields = None
    def get_fields(self, refetch=False):
        if refetch or not(self.cached_fields):
            self.cached_fields = Field.objects.filter(sheet=self, active=True).order_by('order')
        return self.cached_fields
    fields = property(get_fields)

class Field(models.Model, _FormCoherenceMixin):
    label = models.CharField(max_length=60, null=False, blank=False)
    # the sheet this field is a part of
    sheet = models.ForeignKey(Sheet)
    # specifies the order within a sheet
    order = models.PositiveIntegerField()
    fieldtype = models.CharField(max_length=4, choices=FIELD_TYPE_CHOICES, default="SMTX")
    config = JSONField(null=False, blank=False, default={}) # configuration as required by the fieldtype. Must include 'required'
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def autoslug(self):
        return make_slug(self.label)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='sheet')

    def __unicode__(self):
        return "%s, %s" % (self.sheet, self.label)

    def delete(self, *args, **kwargs):
        self.active = False
        self.save()


    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        # if this field is just being created it needs a order number
        if(self.order == None):
            max_aggregate = Field.objects.filter(sheet=self.sheet).aggregate(Max('order'))
            if(max_aggregate['order__max'] == None):
                next_order = 0
            else:
                next_order = max_aggregate['order__max'] + 1
            self.order = next_order


        super(Field, self).save(*args, **kwargs)
        self.cleanup_fields()

def neaten_field_positions(sheet):
    """
    update all positions to consecutive integers: seems possible to get identical positions in some cases
    """
    count = 1
    for f in Field.objects.filter(sheet=sheet, active=True).order_by('order'):
        f.position = count
        f.save()
        count += 1

class FormSubmission(models.Model):
    form = models.ForeignKey(Form)
    initiator = models.ForeignKey(FormFiller)
    owner = models.ForeignKey(FormGroup)
    status = models.CharField(max_length=4, choices=FORM_SUBMISSION_STATUS, default="PEND")
    def autoslug(self):
        return make_slug('submission-' + self.form.slug)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='form')
    
    def update_status(self):
        pass
        # if 'WAIT' in all SheetSubmission.statuses => 'WAIT'
        # unless old status was 'DONE'
    
class SheetSubmission(models.Model):
    form_submission = models.ForeignKey(FormSubmission)
    sheet = models.ForeignKey(Sheet)
    filler = models.ForeignKey(FormFiller)
    status = models.CharField(max_length=4, choices=SUBMISSION_STATUS, default="WAIT")
    given_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    # key = models.CharField()
    def autoslug(self):
        return make_slug('submission-' + self.sheet.slug)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='form_submission')

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        super(SheetSubmission, self).save(*args, **kwargs)
        #self.form_submission.update_status()

    cached_fields = None
    def get_field_submissions(self, refetch=False):
        if refetch or not(self.cached_fields):
            self.cached_fields = FieldSubmission.objects.filter(sheet_submission=self)
        return self.cached_fields
    field_submissions = property(get_field_submissions)

class FieldSubmission(models.Model):
    sheet_submission = models.ForeignKey(SheetSubmission)
    field = models.ForeignKey(Field)
    data = JSONField(null=False, blank=False, default={})

FormSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """

    fullpath = os.path.join(
            'forms',
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.field_submission_id),
            filename.encode('ascii', 'ignore'))
    return fullpath

    
class FieldSubmissionFile(models.Model):
    field_submission = models.ForeignKey(FieldSubmission)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    file_attachment = models.FileField(storage=FormSystemStorage, null=True,
                      upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200, editable=False)

class SheetSubmissionSecretUrl(models.Model):
    sheet_submission = models.ForeignKey(SheetSubmission)
    key = models.CharField(max_length=128, null=False, editable=False, unique=True)

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        if not(self.key):
            self.key = self.autokey()
        super(SheetSubmissionSecretUrl, self).save(*args, **kwargs)

    def autokey(self):
        generated = False
        attempt = str(random.randint(1000,900000000))
        while not(generated):
            old_attemp = attempt
            attempt = sha.new(attempt).hexdigest()
            if len(SheetSubmissionSecretUrl.objects.filter(key=attempt)) == 0:
                generated = True
            elif old_attempt == attempt:
                attempt = str(random.randint(1000,900000000))
        return attempt

    

