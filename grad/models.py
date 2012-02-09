from django.db import models
from coredata.models import Person, Unit, Semester, CAMPUS_CHOICES
from django.forms.models import ModelForm
from django import forms
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from django.template.defaultfilters import capfirst
from django.core.paginator import Page

class GradProgram(models.Model):
    unit = models.ForeignKey(Unit, null=False, blank=False)
    label = models.CharField(max_length=10, null=False)
    description = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    created_by = models.CharField(max_length=32, null=False, help_text='Grad Program created by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Grad Program modified by.')
    def autoslug(self):
        # strip the punctutation entirely
        sluglabel = ''.join((c for c in self.label if c.isalnum()))
        return make_slug(sluglabel)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False)
    class Meta:
        unique_together = (('unit', 'label'),)
    def __unicode__ (self):
        return "%s" % (self.label)

class GradStudent(models.Model):
    person = models.ForeignKey(Person, help_text="Type in student ID or number.", null=False, blank=False, unique=True)
    program = models.ForeignKey(GradProgram, null=False, blank=False)
    def autoslug(self):
        # not sure why we need to have program as part of slug 
        return make_slug(self.person.userid + "-" + self.program.slug)
        #return make_slug(self.person.userid)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False)
    research_area = models.CharField('Research Area', max_length=250, blank=False)
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, blank=True)

    english_fluency = models.CharField(max_length=50, blank=True, help_text="I.e. Read, Write, Speak, All.")
    mother_tongue = models.CharField(max_length=25, blank=True, help_text="I.e. Scottish, Chinese, French")
    is_canadian = models.NullBooleanField()
    passport_issued_by = models.CharField(max_length=25, blank=True, help_text="I.e. US, China")
    special_arrangements = models.NullBooleanField(verbose_name='Special Arrgmnts')
    comments = models.TextField(max_length=250, blank=True, help_text="Additional information.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    created_by = models.CharField(max_length=32, null=False, help_text='Grad Student created by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Grad Student modified by.', verbose_name='Last Modified By')
    def get_fields(self):
        # make a list of field/values.
        k = []
        for field in GradStudent._meta.fields:     
                k.append([capfirst(field.verbose_name), field.value_to_string(self)])
        return k    
    def __unicode__(self):
        return "Grad student: %s" % (self.person)   
    
class Supervisor(models.Model):
    """
    Member (or potential member) of student's supervisory committee.
    """
    student = models.ForeignKey(GradStudent)
    supervisor = models.ForeignKey(Person, help_text="Please choose a Supervisor.")
    external = models.CharField(max_length=200, blank=True, null=True, help_text="Any supervisor not in our records.")
    position = models.SmallIntegerField(null=False)
    is_senior = models.BooleanField()
    is_potential = models.BooleanField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    created_by = models.CharField(max_length=32, null=False, help_text='Supervisor added by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Supervisor modified by.' , verbose_name='Last Modified By')      
    class Meta:
        unique_together = ("student", "position")
    
    def get_fields(self):
        # make a list of field/values.
        k = []
        for field in Supervisor._meta.fields:
            if field.verbose_name == "ID" or field.name == "external":
                pass
            else:
                k.append([capfirst(field.verbose_name), field.value_to_string(self)])
        return k        
    def __unicode__(self):
        return "%s supervising %s" % (self.supervisor or self.external, self.student.person)

    def save_custom(self, *args, **kwargs):
        # make sure the data is coherent: should also be in form validation for nice UI
        is_person = bool(self.supervisor)
        is_ext = bool(self.external)
        if is_person and is_ext:
            raise ValueError, "Cannot be both an SFU user and external"
        if not is_person and not is_ext:
            raise ValueError, "Must be either an SFU user or external"
        
        if self.position == 1 and not self.is_senior:
            raise ValueError, "First supervisor must be senior"
        if self.position == 1 and is_ext:
            raise ValueError, "First supervisor must be internal"
        
        super(Page, self).save(*args, **kwargs)

class GradRequirement(models.Model):
    """
    A requirement that a unit has for grad students
    """
    unit = models.ForeignKey(Unit)
    description = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    def __unicode__(self):
        return "%s" % (self.description)    
        

class CompletedRequirement(models.Model):
    """
    A requirement met by a student (or notes about them meeting it in the future)
    """
    requirement = models.ForeignKey(GradRequirement)
    student = models.ForeignKey(GradStudent)
    semester = models.ForeignKey(Semester, null=True,
            help_text="Semester when the requirement was completed")
    date = models.DateField(null=True, blank=True,
            help_text="Date the requirement was completed (optional)")
    notes = models.TextField(blank=True, help_text="Other notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')    

    def __unicode__(self):
        return "%s" % (self.requirement)

STATUS_CHOICES = (
        ('ACTI', 'Active'),
        ('PART', 'Part-Time'),
        ('LEAV', 'On-Leave'),
        ('WIDR', 'Withdrawn'),
        ('GRAD', 'Graduated'),
        ('NOND', 'Non-degree'),
        ('GONE', 'Gone'),
        )
STATUS_ACTIVE = ('ACTI', 'PART', 'NOND') # statuses that mean "still around"
STATUS_INACTIVE = ('LEAV', 'WIDR', 'GRAD', 'GONE') # statuses that mean "not here"

class GradStatus(models.Model):
    """
    A "status" for a grad student: what were they doing in this range of semesters?
    """
    student = models.ForeignKey(GradStudent)
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, blank=False)
    start = models.ForeignKey(Semester, null=False, related_name="start_semester",
            help_text="First semester of this status")
    end = models.ForeignKey(Semester, null=True, related_name="end_semester",
            help_text="Final semester of this status: blank for ongoing")
    notes = models.TextField(blank=True, help_text="Other notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Grad Status added by.') 

    def get_fields(self):
        # make a list of field/values.
        k = []
        for field in GradStatus._meta.fields:
                k.append([capfirst(field.verbose_name), field.value_to_string(self)])
        return k    
    
    def __unicode__(self):
        return "Grad Status: %s %s" % (self.status, self.student)      
        
