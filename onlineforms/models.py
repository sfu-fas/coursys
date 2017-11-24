import os
from django.db import models
import django.db.transaction
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape as escape
from coredata.models import Person, Unit
from courselib.json_fields import JSONField
from courselib.branding import product_name
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from courselib.json_fields import getter_setter
from courselib.storage import UploadedFileStorage, upload_path
from django.db.models import Max
from django.core.urlresolvers import reverse
from django.conf import settings
from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
import datetime, random, hashlib, itertools, collections

# choices for Form.initiator field
from onlineforms.fieldtypes.other import FileCustomField, DividerField, URLCustomField, ListField, SemesterField, DateSelectField
from onlineforms.fieldtypes.select import DropdownSelectField, RadioSelectField, MultipleSelectField, GradeSelectField
from onlineforms.fieldtypes.text import SmallTextField, MediumTextField, LargeTextField, ExplanationTextField, EmailTextField

INITIATOR_CHOICES = [
        ('LOG', 'Logged-in SFU users'),
        ('ANY', 'Anyone, including non-SFU users'),
        ('NON', 'Nobody: form cannot be filled out'),  # used to deactivate a form, or during creation/editing.
        # may add others if needed, e.g. instructors, admin staff, majors in a specific program, ...
        ]
INITIATOR_SHORT = {
        'LOG': 'SFU Users',
        'ANY': 'Anyone (including non-SFU)',
        'NON': 'Nobody (form disabled)',
        }

# choices for the Sheet.can_view field
VIEWABLE_CHOICES = [
        ('ALL', 'Filler can see all info on previous sheets'),
        ('NON', "Filler can't see any info on other sheets (just name/email of initiator)"),
        ('INI', "Filler can see only the initial sheet"),
        ]
VIEWABLE_SHORT = {
        'ALL': 'Can see info on previous sheets',
        'NON': 'Can only see name/email',
        'INI': 'Can only see initial sheet',
        }

# choices for the Field.fieldtype field
FIELD_TYPE_CHOICES = [
        ('SMTX', 'Small Text (single line)'),
        ('MDTX', 'Medium Text (a few lines)'),
        ('LGTX', 'Large Text (many lines)'),
        ('EMAI', 'Email address'),
        ('RADI', 'Select with radio buttons'),
        ('SEL1', 'Select with a drop-down menu'),
        ('SELN', 'Select multiple values'),
        ('GRAD', 'Select grade (A+ to F)'),
        ('LIST', 'Enter a list of short responses'),
        ('FILE', 'Upload a file'),
        ('URL', 'Web page address (URL)'),
        ('TEXT', 'Explanation block (user enters nothing)'),
        ('DIVI', 'Divider'),
        ('DATE', 'A date'),
        ('SEM', 'Semester'),
        # more may be added.
        ]
FIELD_TYPES = dict(FIELD_TYPE_CHOICES)

# mapping of field types to FieldType objects that implement their logic
FIELD_TYPE_MODELS = {
        'SMTX': SmallTextField,
        'MDTX': MediumTextField,
        'LGTX': LargeTextField,
        'EMAI': EmailTextField,
        'RADI': RadioSelectField,
        'SEL1': DropdownSelectField,
        'SELN': MultipleSelectField,
        'GRAD': GradeSelectField,
        'LIST': ListField,
        'FILE': FileCustomField,
        'URL': URLCustomField,
        'TEXT': ExplanationTextField,
        'DIVI': DividerField,
        'DATE': DateSelectField,
        'SEM': SemesterField,
        }

# mapping of different statuses the forms can be in
SUBMISSION_STATUS = [
        ('WAIT', "Waiting for the user to complete their sheet"),
        ('DONE', "No further action required"),
        ('REJE', "Returned incomplete"),
        ]
        
FORM_SUBMISSION_STATUS = [
        ('PEND', "Waiting for the owner to assign a sheet or mark the form completed"),
        ] + SUBMISSION_STATUS

STATUS_DESCR = {
    'WAIT': 'waiting to be filled in',
    'DONE': 'done',
    'REJE': 'returned incomplete',
    'PEND': 'waiting for admin',
    'NEW': 'newly-created form', # fake value so we can log the new form -> waiting transition correctly
}

class NonSFUFormFiller(models.Model):
    """
    A person without an SFU account that can fill out forms.
    """
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    email_address = models.EmailField(max_length=254)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:

    def __unicode__(self):
        return u"%s, %s" % (self.last_name, self.first_name)
    def name(self):
        return u"%s %s" % (self.first_name, self.last_name)
    def sortname(self):
        return u"%s, %s" % (self.last_name, self.first_name)
    def initials(self):
        return u"%s%s" % (self.first_name[0], self.last_name[0])
    def email(self):
        return self.email_address

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")


class FormFiller(models.Model):
    """
    A wrapper class for filling forms. Is either a SFU account(Person) or a nonSFUFormFiller.
    """
    sfuFormFiller = models.ForeignKey(Person, null=True)
    nonSFUFormFiller = models.ForeignKey(NonSFUFormFiller, null=True)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:

    @classmethod
    def form_email(cls, person):
        """
        Return the email address to use for this Person: honours the form_email config option to let users send
        all form-related email to somewhere else (a role account, probably) while still logging in as the real them.
        """
        assert(isinstance(person, Person))
        if 'form_email' in person.config and person.config['form_email']:
            return person.config['form_email']
        else:
            return person.email()

    @classmethod
    def form_full_email(cls, person):
        email = FormFiller.form_email(person)
        return u"%s <%s>" % (person.name(), email)

    def getFormFiller(self):
        if self.sfuFormFiller:
            return self.sfuFormFiller
        elif self.nonSFUFormFiller:
            return self.nonSFUFormFiller
        else:
            raise ValueError, "This form filler object is in an invalid state."

    def isSFUPerson(self):
        return bool(self.sfuFormFiller)

    def __unicode__(self):
        if self.sfuFormFiller:
            return u"%s (%s)" % (self.sfuFormFiller.name(), self.sfuFormFiller.emplid)
        else:
            return u"%s (external user)" % (self.nonSFUFormFiller.name(),)
    def name(self):
        formFiller = self.getFormFiller()
        return formFiller.name()
    def sortname(self):
        formFiller = self.getFormFiller()
        return formFiller.sortname()
    def initials(self):
        formFiller = self.getFormFiller()
        return formFiller.initials()

    def email(self):
        formFiller = self.getFormFiller()
        if self.sfuFormFiller:
            return FormFiller.form_email(formFiller)
        else:
            return formFiller.email()

    def full_email(self):
        return u"%s <%s>" % (self.name(), self.email())

    def identifier(self):
        """
        Identifying string that can be used for slugs
        """
        if self.sfuFormFiller:
            return self.sfuFormFiller.userid_or_emplid()
        else:
            return self.nonSFUFormFiller.email() \
                   .replace('@', '-').replace('.', '-')

    def emplid(self):
        """
        If this is an SFU user, return the emplid, otherwise, nothing.
        """
        if self.sfuFormFiller:
            return self.sfuFormFiller.emplid
        else:
            return None

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    
    def email_mailto(self):
        "A mailto: URL for this person's email address: handles the case where we don't know an email for them."
        email = self.email()
        if email:
            return mark_safe(u'<a href="mailto:%s">%s</a>' % (escape(email), escape(email)))
        else:
            return "None"

class FormGroup(models.Model):
    """
    A group that owns forms and form submissions.
    """
    unit = models.ForeignKey(Unit)
    name = models.CharField(max_length=60, null=False, blank=False)
    members = models.ManyToManyField(Person, through='FormGroupMember') #
    def autoslug(self):
        return make_slug(self.unit.label + ' ' + self.name)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    class Meta:
        unique_together = (("unit", "name"),)

    def __unicode__(self):
        return u"%s, %s" % (self.name, self.unit.label)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."

    def notify_emails(self):
        """
        Collection of emails to notify about something in this group
        """
        return [FormFiller.form_full_email(m.person)
              for m
              in self.formgroupmember_set.all()
              if m.email()]

class FormGroupMember(models.Model):
    """
    Member of a FormGroup. Upgraded for simple ManyToManyField so we have the .config

    Do not use as a foreign key: is deleted when people leave the FormGroup
    """
    person = models.ForeignKey(Person)
    formgroup = models.ForeignKey(FormGroup)
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff:
        # 'email': should this member receive emails on completed sheets?

    defaults = {'email': True}
    email, set_email = getter_setter('email')

    class Meta:
        db_table = 'onlineforms_formgroup_members' # to make it Just Work with the FormGroup.members without "through=" that existed previously
        unique_together = (("person", "formgroup"),)

    def __unicode__(self):
        return u"%s in %s" % (self.person.name(), self.formgroup.name)


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
    title = models.CharField(max_length=60, null=False, blank=False, help_text='The name of this form.')
    owner = models.ForeignKey(FormGroup, help_text='The group of users who own/administrate this form.')
    description = models.CharField(max_length=500, null=False, blank=False, help_text='A brief description of the form that can be displayed to users.')
    initiators = models.CharField(max_length=3, choices=INITIATOR_CHOICES, default="NON", help_text='Who is allowed to fill out the initial sheet? That is, who can initiate a new instance of this form?')
    unit = models.ForeignKey(Unit)
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    advisor_visible = models.BooleanField(default=False, help_text="Should submissions be visible to advisors in this unit?")
    def autoslug(self):
        return make_slug(self.unit.label + ' ' + self.title)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # 'loginprompt': should the "log in with your account" prompt be displayed for non-logged-in? (default True)
        # 'unlisted':  Form can be filled out, but doesn't show up in the index
        # 'jsfile':  Extra Javascript file included with this form.  USE THIS CAREFULLY.  There is no validation here, and
        # this should be used extremely rarely by sysadmins only.  There should never be any UI to modify this by users.

    defaults = {'loginprompt': True, 'unlisted': False, 'jsfile': None}
    loginprompt, set_loginprompt = getter_setter('loginprompt')
    unlisted, set_unlisted = getter_setter('unlisted')
    jsfile, set_jsfile = getter_setter('jsfile')

    def __unicode__(self):
        return u"%s [%s]" % (self.title, self.id)
    
    def delete(self, *args, **kwargs):
        self.active = False
        self.save()

    def save(self, *args, **kwargs):
        with django.db.transaction.atomic():
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

    def get_initiators_display_short(self):
        return INITIATOR_SHORT[self.initiators]

    def duplicate(self):
        """
        Make a independent duplicate of this form.

        Not called from the UI anywhere, but can be used to duplicate a form for another unit, without the pain of
        re-creating everything:
            newform = oldform.duplicate()
            newform.owner = ...
            newform.unit = ...
            newform.initiators = ...
            newform.slug = None
            newform.save()
        """
        with django.db.transaction.atomic():
            newform = self.clone()
            newform.original = None
            newform.slug = None
            newform.active = True
            newform.initiators = 'NON'
            newform.save()

            sheets = Sheet.objects.filter(form=self)
            for s in sheets:
                newsheet = s.clone()
                newsheet.form = newform
                newsheet.original = None
                newsheet.slug = None
                newsheet.save()

                fields = Field.objects.filter(sheet=s)
                for f in fields:
                    newfield = f.clone()
                    newfield.sheet = newsheet
                    newfield.original = None
                    newfield.slug = None
                    newfield.save()

            return newform

    def all_submission_summary(self):
        """
        Generate summary data of each submission for CSV output
        """
        DATETIME_FMT = "%Y-%m-%d"
        headers = []
        data = []

        # find all sheets (in a sensible order: deleted last)
        sheets = Sheet.objects.filter(form__original_id=self.original_id).order_by('order', '-created_date')
        active_sheets = [s for s in sheets if s.active]
        inactive_sheets = [s for s in sheets if not s.active]
        sheet_info = collections.OrderedDict()
        for s in itertools.chain(active_sheets, inactive_sheets):
            if s.original_id not in sheet_info:
                sheet_info[s.original_id] = {
                    'title': s.title,
                    'fields': collections.OrderedDict(),
                    'is_initial': s.is_initial,
                }

        # find all fields in each of those sheets (in a equally-sensible order)
        fields = Field.objects.filter(sheet__form__original_id=self.original_id).select_related('sheet').order_by('order', '-created_date')
        active_fields = [f for f in fields if f.active]
        inactive_fields = [f for f in fields if not f.active]
        for f in itertools.chain(active_fields, inactive_fields):
            if not FIELD_TYPE_MODELS[f.fieldtype].in_summary:
                continue
            info = sheet_info[f.sheet.original_id]
            if f.original_id not in info['fields']:
                info['fields'][f.original_id] = {
                    'label': f.label,
                }

        # build header row
        for sid, info in sheet_info.iteritems():
            headers.append(info['title'].upper())
            headers.append(None)
            headers.append('ID')
            if info['is_initial']:
                headers.append('Initiated')
            for fid, finfo in info['fields'].iteritems():
                headers.append(finfo['label'])
        headers.append('Last Sheet Completed')
        headers.append('Link')

        # go through FormSubmissions and create a row for each
        formsubs = FormSubmission.objects.filter(form__original_id=self.original_id, status='DONE') \
                .select_related('initiator__sfuFormFiller', 'initiator__nonSFUFormFiller', 'form')
                # selecting only fully completed forms: does it make sense to be more liberal and report status?

        # choose a winning SheetSubmission: there may be multiples of each sheet but we're only outputting one
        sheetsubs = SheetSubmission.objects.filter(form_submission__form__original_id=self.original_id, status='DONE') \
                .order_by('given_at').select_related('sheet', 'filler__sfuFormFiller', 'filler__nonSFUFormFiller')
        # Docs for the dict constructor: "If a key occurs more than once, the last value for that key becomes the corresponding value in the new dictionary."
        # Result is that the sheetsub with most recent given_at wins.
        winning_sheetsub = dict(
            ((ss.form_submission_id, ss.sheet.original_id), ss)
            for ss in sheetsubs)

        # collect fieldsubs to output
        fieldsubs = FieldSubmission.objects.filter(sheet_submission__form_submission__form__original_id=self.original_id) \
                .order_by('sheet_submission__given_at') \
                .select_related('sheet_submission', 'field')
        fieldsub_lookup = dict(
            ((fs.sheet_submission_id, fs.field.original_id), fs)
            for fs in fieldsubs)

        for formsub in formsubs:
            row = []
            found_anything = False
            last_completed = None
            for sid, info in sheet_info.iteritems():
                if (formsub.id, sid) in winning_sheetsub:
                    ss = winning_sheetsub[(formsub.id, sid)]
                    row.append(ss.filler.name())
                    row.append(ss.filler.email())
                    row.append(ss.filler.emplid())
                    if not last_completed or ss.completed_at > last_completed:
                        last_completed = ss.completed_at
                else:
                    ss = None
                    row.append(None)
                    row.append(None)
                    row.append(None)

                if info['is_initial']:
                    if ss:
                        row.append(ss.given_at.strftime(DATETIME_FMT))
                    else:
                        row.append(None)

                for fid, finfo in info['fields'].iteritems():
                    if ss and (ss.id, fid) in fieldsub_lookup:
                        fs = fieldsub_lookup[(ss.id, fid)]
                        handler = FIELD_TYPE_MODELS[fs.field.fieldtype](fs.field.config)
                        row.append(handler.to_text(fs))
                        found_anything = True
                    else:
                        row.append(None)

            if last_completed:
                row.append(last_completed.strftime(DATETIME_FMT))
            else:
                row.append(None)

            row.append(settings.BASE_ABS_URL + formsub.get_absolute_url())

            if found_anything:
                data.append(row)

        return headers, data


class Sheet(models.Model, _FormCoherenceMixin):
    title = models.CharField(max_length=60, null=False, blank=False)
    # the form this sheet is a part of
    form = models.ForeignKey(Form)
    # specifies the order within a form
    order = models.PositiveIntegerField()
    # Flag to indicate whether this is the first sheet in the form
    is_initial = models.BooleanField(default=False)
    # indicates whether a person filling a sheet can see the results from all the previous sheets
    can_view = models.CharField(max_length=4, choices=VIEWABLE_CHOICES, default="NON", help_text='When someone is filling out this sheet, what else can they see?')
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
    
    def autoslug(self):
        return make_slug(self.title)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='form')

    #class Meta:
    #    unique_together = (('form', 'order'),)

    def __unicode__(self):
        return u"%s, %s [%i]" % (self.form, self.title, self.id)

    def delete(self, *args, **kwargs):
        if self.is_initial == True:
            raise NotImplementedError
        else:
            self.active = False
            self.save()

    class Meta:
        unique_together = (("form", "slug"),)
        ordering = ('order',)

    def safe_save(self):
        """
        Save a copy of this sheet, and return the copy: does not modify self.
        """
        with django.db.transaction.atomic():
            # clone the sheet
            sheet2 = self.clone()
            self.slug = self.slug + "_" + str(self.id)
            self.save()
            sheet2.save()
            sheet2.cleanup_fields()
            # copy the fields
            for field1 in Field.objects.filter(sheet=self, active=True):
                field2 = field1.clone()
                field2.sheet = sheet2
                field2.save()
            return sheet2       

    def save(self, *args, **kwargs):
        with django.db.transaction.atomic():
            # if this sheet is just being created it needs a order number
            if(self.order == None):
                max_aggregate = Sheet.objects.filter(form=self.form).aggregate(Max('order'))
                if(max_aggregate['order__max'] == None):
                    next_order = 0
                    # making first sheet for form--- initial 
                    self.is_initial = True
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
    
    def get_can_view_display_short(self):
        return VIEWABLE_SHORT[self.can_view]

class Field(models.Model, _FormCoherenceMixin):
    label = models.CharField(max_length=60, null=False, blank=False)
    # the sheet this field is a part of
    sheet = models.ForeignKey(Sheet)
    # specifies the order within a sheet
    order = models.PositiveIntegerField()
    fieldtype = models.CharField(max_length=4, choices=FIELD_TYPE_CHOICES, default="SMTX")
    config = JSONField(null=False, blank=False, default=dict) # configuration as required by the fieldtype. Must include 'required'
    active = models.BooleanField(default=True)
    original = models.ForeignKey('self', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    def autoslug(self):
        return make_slug(self.label)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='sheet')

    def __unicode__(self):
        return u"%s, %s" % (self.sheet, self.label)

    def delete(self, *args, **kwargs):
        self.active = False
        self.save()

    class Meta:
        unique_together = (("sheet", "slug"),)

    def save(self, *args, **kwargs):
        with django.db.transaction.atomic():
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
        return self.initiator.identifier()
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='form')
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # 'summary': summary of the form entered when closing it
        # 'emailed': True if the initiator was emailed when the form was closed
        # 'closer': coredata.Person.id of the person that marked the formsub as DONE

    defaults = {'summary': '', 'emailed': False, 'closer': None}
    summary, set_summary = getter_setter('summary')
    emailed, set_emailed = getter_setter('emailed')
    closer_id, set_closer = getter_setter('closer')

    def update_status(self):
        sheet_submissions = SheetSubmission.objects.filter(form_submission=self)
        orig_status = self.status
        if all(sheet_sub.status in ['DONE', 'REJE'] for sheet_sub in sheet_submissions):
            self.status = 'PEND'
        else:
            self.status = 'WAIT'

        if orig_status != self.status:
            # log status change
            FormLogEntry.create(form_submission=self, category='AUTO',
                    description=u'System changed form status from "%s" to "%s".'
                                % (STATUS_DESCR[orig_status], STATUS_DESCR[self.status]))

        self.save()

    def __unicode__(self):
        return u"%s for %s" % (self.form, self.initiator)

    def get_absolute_url(self):
        return reverse('onlineforms:view_submission', kwargs={'form_slug': self.form.slug,'formsubmit_slug': self.slug})

    def closer(self):
        try:
            return Person.objects.get(id=self.closer_id())
        except Person.DoesNotExist:
            return None
    
    def last_sheet_completion(self):
        if hasattr(self, 'last_sheet_dt'):
            # use the one annotated in here by .annotate(last_sheet_dt=Max('sheetsubmission__completed_at'))
            return self.last_sheet_dt

        # In the case of closed forms, we probably care about when the form was actually closed. Finding the last
        # FormLogEntry with category 'ADMN' should hopefully tell us that.
        if self.status == 'DONE' and self.formlogentry_set.filter(category='ADMN').count() > 0:
            return self.formlogentry_set.filter(category='ADMN').last().timestamp

        return self.sheetsubmission_set.all().aggregate(Max('completed_at'))['completed_at__max']

    def email_notify_completed(self, request, admin):
        plaintext = get_template('onlineforms/emails/notify_completed.txt')
        html = get_template('onlineforms/emails/notify_completed.html')

        email_context = Context({'formsub': self, 'admin': admin})
        subject = '%s for %s submission complete' % (self.form.title, self.initiator.name())
        from_email = FormFiller.form_full_email(admin)
        to = self.initiator.full_email()
        msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                from_email=from_email, to=[to], bcc=[admin.full_email()],
                headers={'X-coursys-topic': 'onlineforms'})
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()

        FormLogEntry.create(form_submission=self, category='MAIL',
                    description=u'Notified %s that form submission was completed by %s.'
                                % (to, from_email))

    def email_notify_new_owner(self, request, admin):
        plaintext = get_template('onlineforms/emails/notify_new_owner.txt')
        html = get_template('onlineforms/emails/notify_new_owner.html')

        full_url = request.build_absolute_uri(reverse('onlineforms:view_submission',
                                    kwargs={'form_slug': self.form.slug,
                                            'formsubmit_slug': self.slug}))
        email_context = Context({'formsub': self, 'admin': admin, 'adminurl': full_url})
        subject = u'%s submission transferred' % (self.form.title)
        from_email = FormFiller.form_full_email(admin)
        to = self.owner.notify_emails()
        msg = EmailMultiAlternatives(subject=subject, body=plaintext.render(email_context),
                from_email=from_email, to=to, bcc=[admin.full_email()],
                headers={'X-coursys-topic': 'onlineforms'})
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()

        FormLogEntry.create(form_submission=self, category='MAIL',
                    description=u'Notified group "%s" that form submission was transferred to them.'
                                % (self.owner.name,))


class SheetSubmission(models.Model):
    form_submission = models.ForeignKey(FormSubmission)
    sheet = models.ForeignKey(Sheet)
    filler = models.ForeignKey(FormFiller)
    status = models.CharField(max_length=4, choices=SUBMISSION_STATUS, default="WAIT")
    given_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    # key = models.CharField()
    def autoslug(self):
        return self.filler.identifier()
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='form_submission')
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:
        # 'assigner': the user who assigned this sheet to the filler (Person.id value)
        # 'assign_note': optional note provided for asignee when sheet was assigned by admin
        # 'assign_comment': optional comment provided by admin about the formsubmission
        # 'reject_reason': reason given for rejecting the sheet
        # 'return_reason': reason given for returning the sheet to the filler

    def save(self, *args, **kwargs):
        with django.db.transaction.atomic():
            self.completed_at = datetime.datetime.now()
            super(SheetSubmission, self).save(*args, **kwargs)
            self.form_submission.update_status()

    def __unicode__(self):
        return u"%s by %s" % (self.sheet, self.filler.identifier())
    
    defaults = {'assigner': None, 'assign_comment': None, 'assign_note': None, 'reject_reason': None, 'return_reason': None}
    assigner_id, set_assigner_id = getter_setter('assigner')
    assign_note, set_assign_note = getter_setter('assign_note')
    assign_comment, set_assign_comment = getter_setter('assign_comment')
    reject_reason, set_reject_reason = getter_setter('reject_reason')
    return_reason, set_return_reason = getter_setter('return_reason')

    cached_fields = None
    def get_field_submissions(self, refetch=False):
        if refetch or not(self.cached_fields):
            self.cached_fields = FieldSubmission.objects.filter(sheet_submission=self)
        return self.cached_fields
    field_submissions = property(get_field_submissions)

    def assigner(self):
        assigner_id = self.assigner_id()
        if assigner_id:
            return Person.objects.get(id=assigner_id)
        else:
            return None

    def set_assigner(self, assigner):
        self.set_assigner_id(assigner.id)

    def get_secret(self):
        try:
            return SheetSubmissionSecretUrl.objects.get(sheet_submission=self)
        except SheetSubmissionSecretUrl.DoesNotExist:
            return None

    def get_submission_url(self):
        """
        Creates a URL for a sheet submission.
        If a secret URL has been generated it will use that,
        otherwise it will create a standard URL.
        """
        secret_urls = SheetSubmissionSecretUrl.objects.filter(sheet_submission=self)
        if secret_urls:
            return reverse('onlineforms:sheet_submission_via_url', kwargs={'secret_url': secret_urls[0].key})
        else:
            return reverse('onlineforms:sheet_submission_subsequent', kwargs={
                                'form_slug': self.form_submission.form.slug,
                                'formsubmit_slug': self.form_submission.slug,
                                'sheet_slug': self.sheet.slug,
                                'sheetsubmit_slug': self.slug})


    @classmethod
    def sheet_maintenance(cls):
        """
        Do all of the stuff we need to update on a regular basis.
        """
        cls.reject_dormant_initial()
        cls.email_waiting_sheets()

    @classmethod
    def reject_dormant_initial(cls):
        """
        Close any initial sheets that have been hanging around for too long.
        """
        days = 14
        min_age = datetime.datetime.now() - datetime.timedelta(days=days)
        sheetsubs = SheetSubmission.objects.filter(sheet__is_initial=True, status='WAIT', given_at__lt=min_age)
        for ss in sheetsubs:
            ss.status = 'REJE'
            ss.set_reject_reason('Automatically closed by system after being dormant %i days.' % (days))
            ss.save()

            fs = ss.form_submission
            fs.status = 'DONE'
            fs.set_summary('Automatically closed by system after being dormant %i days.' % (days))
            fs.save()

            FormLogEntry.create(sheet_submission=ss, category='SYST',
                        description=u'Automatically closed dormant draft form.')

    @classmethod
    def waiting_sheets_by_user(cls):
        min_age = datetime.datetime.now() - datetime.timedelta(hours=24)
        sheet_subs = SheetSubmission.objects.exclude(status='DONE').exclude(status='REJE') \
                .exclude(given_at__gt=min_age) \
                .order_by('filler__id') \
                .select_related('filler__sfuFormFiller', 'filler__nonSFUFormFiller', 'form_submission__initiator', 'form_submission__form', 'sheet')
        return itertools.groupby(sheet_subs, lambda ss: ss.filler)

    @classmethod
    def email_waiting_sheets(cls):
        """
        Email those with sheets waiting for their attention.
        """
        full_url = settings.BASE_ABS_URL + reverse('onlineforms:login')
        subject = 'Waiting form reminder'
        from_email = settings.DEFAULT_FROM_EMAIL

        filler_ss = cls.waiting_sheets_by_user()
        template = get_template('onlineforms/emails/reminder.txt')
        
        for filler, sheets in filler_ss:
            # annotate with secret URL, so we can remind of that.
            sheets = list(sheets)
            for s in sheets:
                secrets = SheetSubmissionSecretUrl.objects.filter(sheet_submission=s)
                if secrets:
                    s.secret = secrets[0]
                else:
                    s.secret = None

                FormLogEntry.create(sheet_submission=s, category='MAIL',
                        description=u'Reminded %s of waiting sheet.' % (filler.email()))

            context = Context({'full_url': full_url,
                    'filler': filler, 'sheets': list(sheets), 'BASE_ABS_URL': settings.BASE_ABS_URL,
                    'CourSys': product_name(hint='forms')})
            msg = EmailMultiAlternatives(subject, template.render(context), from_email, [filler.email()],
                    headers={'X-coursys-topic': 'onlineforms'})
            msg.send()
    
    def _send_email(self, request, template_name, subject, mail_from, mail_to, context):
        """
        Send email to user as required in various places below.
        """
        plaintext = get_template('onlineforms/emails/' + template_name + '.txt')
        html = get_template('onlineforms/emails/' + template_name + '.html')

        sheeturl = request.build_absolute_uri(self.get_submission_url())
        context['sheeturl'] = sheeturl
        context['CourSys'] = product_name(hint='forms')
        email_context = Context(context)
        msg = EmailMultiAlternatives(subject, plaintext.render(email_context), mail_from, mail_to,
                headers={'X-coursys-topic': 'onlineforms'})
        msg.attach_alternative(html.render(email_context), "text/html")
        msg.send()

    def email_assigned(self, request, admin, assignee):
        full_url = request.build_absolute_uri(self.get_submission_url())
        context = {'username': admin.name(), 'assignee': assignee.name(), 'sheeturl': full_url, 'sheetsub': self}
        subject = '%s: You have been assigned a sheet in a form submitted by %s.' % (product_name(hint='forms'),
                                                                                     self.form_submission.initiator.name())
        self._send_email(request, 'sheet_assigned', subject, FormFiller.form_full_email(admin),
                         [assignee.full_email()], context)

        FormLogEntry.create(sheet_submission=self, category='MAIL',
                        description=u'Notified %s that they were assigned a sheet.' % (assignee.full_email(),))

    def email_started(self, request):
        full_url = request.build_absolute_uri(self.get_submission_url())
        context = {'initiator': self.filler.name(), 'sheeturl': full_url, 'sheetsub': self}
        subject = u'%s submission incomplete' % (self.sheet.form.title)
        self._send_email(request, 'nonsfu_sheet_started', subject,
                         settings.DEFAULT_FROM_EMAIL, [self.filler.full_email()], context)

        FormLogEntry.create(sheet_submission=self, category='MAIL',
                        description=u'Notified %s that they saved an incomplete sheet.' % (self.filler.full_email(),))

    def email_submitted(self, request, rejected=False):
        full_url = request.build_absolute_uri(reverse('onlineforms:view_submission',
                                    kwargs={'form_slug': self.sheet.form.slug,
                                            'formsubmit_slug': self.form_submission.slug}))
        context = {'initiator': self.filler.name(), 'adminurl': full_url, 'form': self.sheet.form,
                                 'rejected': rejected}
        subject = u'%s submission' % (self.sheet.form.title)
        self._send_email(request, 'sheet_submitted', subject,
                         settings.DEFAULT_FROM_EMAIL, self.sheet.form.owner.notify_emails(), context)

        FormLogEntry.create(sheet_submission=self, category='MAIL',
                description=u'Notified group "%s" that %s %s their sheet.' % (self.sheet.form.owner.name,
                        self.filler.full_email(), 'rejected' if rejected else 'completed'))

    def email_returned(self, request, admin):
        context = {'admin': admin, 'sheetsub': self}
        self._send_email(request, 'sheet_returned', u'%s submission returned' % (self.sheet.title),
                         FormFiller.form_full_email(admin), [self.filler.full_email()], context)

        FormLogEntry.create(sheet_submission=self, category='MAIL',
                description=u'Notified %s of returned sheet.' % (self.filler.full_email(),))


class FieldSubmission(models.Model):
    sheet_submission = models.ForeignKey(SheetSubmission)
    field = models.ForeignKey(Field)
    data = JSONField(null=False, blank=False, default={})
    
    __file_sub_cache = None
    def file_sub(self):
        """
        Return the (most recent) FieldSubmissionFile associated with this FieldSubmission, or None
        """
        assert self.field.fieldtype == 'FILE'
        if self.__file_sub_cache:
            # don't look up the same thing a lot unnecessarily
            return self.__file_sub_cache
        
        file_subs = FieldSubmissionFile.objects.filter(field_submission=self) \
                    .order_by('-created_at')[0:1]
        if file_subs:
            self.__file_sub_cache = file_subs[0]
            return self.__file_sub_cache
        else:
            return None
        

def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """
    return upload_path('forms', instance.field_submission.sheet_submission.form_submission.form.slug, filename)

    
class FieldSubmissionFile(models.Model):
    field_submission = models.OneToOneField(FieldSubmission)
    created_at = models.DateTimeField(default=datetime.datetime.now)
    file_attachment = models.FileField(storage=UploadedFileStorage, null=True,
                      upload_to=attachment_upload_to, blank=True, max_length=500)
    file_mediatype = models.CharField(null=True, blank=True, max_length=200, editable=False)
    
    def get_file_url(self):
        return reverse('onlineforms:file_field_download',
                       kwargs={'form_slug': self.field_submission.sheet_submission.sheet.form.slug,
                               'formsubmit_slug': self.field_submission.sheet_submission.form_submission.slug,
                               'file_id': self.id,
                               'action': 'get'})
    def display_filename(self):
        return os.path.basename(self.file_attachment.file.name)

class SheetSubmissionSecretUrl(models.Model):
    sheet_submission = models.ForeignKey(SheetSubmission)
    key = models.CharField(max_length=128, null=False, editable=False, unique=True)

    def save(self, *args, **kwargs):
        with django.db.transaction.atomic():
            if not(self.key):
                self.key = self.autokey()
            super(SheetSubmissionSecretUrl, self).save(*args, **kwargs)

    def autokey(self):
        generated = False
        attempt = str(random.randint(1000,900000000))
        while not(generated):
            old_attempt = attempt
            attempt = hashlib.sha1(attempt).hexdigest()
            if len(SheetSubmissionSecretUrl.objects.filter(key=attempt)) == 0:
                generated = True
            elif old_attempt == attempt:
                attempt = str(random.randint(1000,900000000))
        return attempt

FORMLOG_CATEGORIES = [
    ('AUTO', 'Automatic update'), # ... that is probably for internal record-keeping only.
    ('SYST', 'Automatic change by system'), # ... that the end-users might care about.
    ('MAIL', 'Email notification sent'),
    ('ADMN', 'Administrative action'),
    ('FILL', 'User action'),
    ('SAVE', 'Saved draft'),
]

class FormLogEntry(models.Model):
    """
    Model to represent a thing that happened to FormSubmission, so we can show the user a unified history.
    """
    form_submission = models.ForeignKey(FormSubmission, null=False)
    sheet_submission = models.ForeignKey(SheetSubmission, null=True)

    # one of user and externalFiller should always be null; both null == system-caused event.
    user = models.ForeignKey(Person, null=True, help_text='User who took the action/made the change')
    externalFiller = models.ForeignKey(NonSFUFormFiller, null=True)

    timestamp = models.DateTimeField(default=timezone.now)
    category = models.CharField(max_length=4, choices=FORMLOG_CATEGORIES)
    description = models.CharField(max_length=255, help_text="Description of the action/change")
    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff:

    class Meta:
        ordering = ('timestamp',)

    @classmethod
    def create(cls, category, description, user=None, filler=None, form_submission=None, sheet_submission=None):
        """
        Create and save a FormLogEntry.

        May specify either form_submission or sheet_submission (and then form_submission is implied).

        May specify either user (a Person) or filler (a FormFiller) or neither (for system event).
        """
        # TODO: do we really need to save category__in=['AUTO', 'MAIL', 'SAVE'] since they are never displayed?

        if not form_submission:
            if sheet_submission and sheet_submission.form_submission:
                form_submission = sheet_submission.form_submission
            else:
                raise ValueError, 'Must pass either sheet_submission or form_submission so we have the FormSubmission.'

        if user and filler:
            raise ValueError, 'Cannot set both user and filler.'
        elif filler and not user:
            if filler.isSFUPerson():
                user = filler.sfuFormFiller
                externalFiller = None
            else:
                user = None
                externalFiller = filler.nonSFUFormFiller
        else:
            externalFiller = None

        le = FormLogEntry(form_submission=form_submission, sheet_submission=sheet_submission, user=user,
                externalFiller=externalFiller, category=category, description=description)
        le.save()
        return le

    def __unicode__(self):
        return u'Log %s formsub %s sheetsub %s by %s: "%s"' % (self.category, self.form_submission_id,
                self.sheet_submission_id, self.identifier(), self.description)

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because its job is to exist."

    @property
    def completed_at(self):
        """
        Fake a .completed_at so we can sort these and SheetSubmissions by obj.completed_at.

        Fudge a little later to make sure log entries are displayed after the completed sheet, not before.
        """
        return self.timestamp + datetime.timedelta(seconds=1)

    def identifier(self):
        if self.user:
            return self.user.userid_or_emplid()
        elif self.externalFiller:
            return self.externalFiller.email_address
        else:
            return '*system*'


ORDER_TYPE = {'UP': 'up', 'DN': 'down'}

def reorder_sheet_fields(ordered_fields, field_slug, order):
    """
    Reorder the activity in the field list of a course according to the
    specified order action. Please make sure the field list belongs to
    the same sheet.
    """
    for field in ordered_fields:
        if not isinstance(field, Field):
            raise TypeError(u'ordered_fields should be list of Field')
    for i in range(0, len(ordered_fields)):
        if ordered_fields[i].slug == field_slug:
            if (order == ORDER_TYPE['UP']) and (not i == 0):
                # swap order
                temp = ordered_fields[i-1].order
                ordered_fields[i-1].order = ordered_fields[i].order
                ordered_fields[i].order = temp
                ordered_fields[i-1].save()
                ordered_fields[i].save()
            elif (order == ORDER_TYPE['DN']) and (not i == len(ordered_fields) - 1):
                # swap order
                temp = ordered_fields[i+1].order
                ordered_fields[i+1].order = ordered_fields[i].order
                ordered_fields[i].order = temp
                ordered_fields[i+1].save()
                ordered_fields[i].save()
            break


