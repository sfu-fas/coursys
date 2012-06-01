from django.db import models
from coredata.models import Person, Unit, Semester, CAMPUS_CHOICES
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from courselib.json_fields import getter_setter
from django.template.defaultfilters import capfirst
from jsonfield import JSONField

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
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with=('unit',))
    class Meta:
        unique_together = (('unit', 'label'),)
    def __unicode__ (self):
        return u"%s" % (self.label)

APPLICATION_STATUS_CHOICES = (
        ('INCO', 'Incomplete'),
        ('COMP', 'Complete'),
        ('INRE', 'In-Review'),
        ('HOLD', 'Hold'),
        ('OFFO', 'Offer Out'),
        ('REJE', 'Rejected'),
        ('DECL', 'Declined Offer'),
        ('EXPI', 'Expired'),
        ('CONF', 'Confirmed'),
        ('CANC', 'Cancelled'),
        ('UNKN', 'Unknown'),
        )
# order: In-Review, rej/dec? , expired, cancelled, confirmed, unknown

class GradStudent(models.Model):
    person = models.ForeignKey(Person, help_text="Type in student ID or number.", null=False, blank=False, unique=False)
    program = models.ForeignKey(GradProgram, null=False, blank=False)
    def autoslug(self):
        if self.person.userid:
            userid = self.person.userid
        else:
            userid = str(self.person.emplid)
        return make_slug(userid + "-" + self.program.slug)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    research_area = models.TextField('Research Area', blank=True)
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, blank=True)

    english_fluency = models.CharField(max_length=50, blank=True, help_text="I.e. Read, Write, Speak, All.")
    mother_tongue = models.CharField(max_length=25, blank=True, help_text="I.e. Scottish, Chinese, French")
    is_canadian = models.NullBooleanField()
    passport_issued_by = models.CharField(max_length=25, blank=True, help_text="I.e. US, China")
    special_arrangements = models.NullBooleanField(verbose_name='Special Arrgmnts')
    comments = models.TextField(max_length=250, blank=True, help_text="Additional information.")
    application_status = models.CharField(max_length=4, choices=APPLICATION_STATUS_CHOICES, default='UNKN')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    created_by = models.CharField(max_length=32, null=False, help_text='Grad Student created by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Grad Student modified by.', verbose_name='Last Modified By')

    config = JSONField(default={}) # addition configuration
        # 'sin': Social Insurance Number
        # 'app_id': unique identifier for the PCS application import (so we can detect duplicate imports)
        # 'start_semester': first semester of project (if known from PCS import), as a semester.name (e.g. '1127')
    defaults = {'sin': '000000000'}
    sin, set_sin = getter_setter('sin')

    def get_fields(self):
        # make a list of field/values.
        k = []
        for field in GradStudent._meta.fields:     
                k.append([capfirst(field.verbose_name), field.value_to_string(self)])
        return k    
    def __unicode__(self):
        return u"Grad student: %s" % (self.person)
    def save(self, *args, **kwargs):
        # rebuild slug in case something changes
        self.slug = None
        super(GradStudent, self).save(*args, **kwargs)
    
    def start_semester(self):
        """
        Semester this student started
        """
        # do we actually know?
        if 'start_semester' in self.config:
            return Semester.objects.get(name=self.config['start_semester'])
        # first active semester
        active = GradStatus.objects.filter(student=self, status__in=STATUS_ACTIVE).order_by('start')
        if active:
            return active[0].start
        # semester after application
        applic = GradStatus.objects.filter(student=self, status='APPL').order_by('start')
        if applic:
            return applic[0].start.next_semester()
        # next semester
        return Semester.current().next_semester()
        
    def letter_info(self):
        gender = self.person.gender()
        #addresses = self.person.addresses()
    
        #if 'home' in addresses:
        #    address = addresses['home']
        #elif 'work' in addresses:
        #    address = addresses['work']
        #else:
        #    address = ''
    
        if gender == "M" :
            hisher = "his"
        elif gender == "F":
            hisher = "her"
        else:
            hisher = "his/her"
        Hisher = hisher.title()
        
        promises = Promise.objects.filter(student=self).order_by('-start_semester')
        if promises:
            try:
                promise = "${:,f}".format(promises[0].amount)
            except ValueError: # handle Python <2.7
                promise = '$' + unicode(promises[0].amount)
        else:
            promise = u'$0'
        
        startsem = self.start_semester()
        if startsem:
            startsem = startsem.label()
        else:
            startsem = 'UNKNOWN'
        
        ls = {
                'title' : self.person.get_title(),
                'his_her' : hisher,
                'His_Her' : Hisher,
                'first_name': self.person.first_name,
                'last_name': self.person.last_name,
                #'address':  address,
                'promise': promise,
                'start_semester': startsem,
                #'empl_data': "OO type of employment RA, TA OO",
                #'fund_type': "OO RA / TA / Scholarship]]",
                #'fund_amount_sem': "OO amount of money paid per semester OO",
                'program': self.program.description,
              }
        return ls

# documentation for the fields returned by GradStudent.letter_info
LETTER_TAGS = {
               'title': '"Mr", "Miss", etc.',
               'first_name': 'student\'s first name',
               'last_name': 'student\'s last name',
               #'address': 'includes street, city/province/postal, country',
               #'empl_data': 'type of employment RA, TA',
               #'fund_type': 'RA, TA, Scholarship',
               #'fund_amount_sem': 'amount of money paid per semester',
               'his_her' : '"his" or "her" (or use His_Her for capitalized)',
               'program': 'the program the student is enrolled in',
               'start_semester': 'student\'s first semester (e.g. "Summer 2000")',
               'promise': 'the amount of the (most recent) funding promise to the student (e.g. "$17,000")',
               }

SUPERVISOR_TYPE_CHOICES = [
                           ('SEN', 'Senior Supervisor'),
                           ('COM', 'Committee Member'),
                           ('POT', 'Potential Supervisor'),
                           ('CHA', 'Defence Chair'),
                           ('EXT', 'External Examiner'),
                           ('SFU', 'SFU Examiner'),
                           ]
class Supervisor(models.Model):
    """
    Member (or potential member) of student's supervisory committee.
    """
    student = models.ForeignKey(GradStudent)
    supervisor = models.ForeignKey(Person, blank=True, null=True, help_text="Please choose a Supervisor.")
    external = models.CharField(max_length=200, blank=True, null=True, help_text="Any non-SFU supervisor.")
    position = models.SmallIntegerField(null=False)
    #is_senior = models.BooleanField()
    #is_potential = models.BooleanField()
    supervisor_type = models.CharField(max_length=3, blank=False, null=False, choices=SUPERVISOR_TYPE_CHOICES)
    removed = models.BooleanField(default=False) # TODO: actually use removed flag instead of deleting
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    created_by = models.CharField(max_length=32, null=False, help_text='Supervisor added by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Supervisor modified by.', verbose_name='Last Modified By')
    config = JSONField(default={}) # addition configuration
        # 'email': Email address (for external)
    defaults = {'email': None}
    email, set_email = getter_setter('email')
          
    class Meta:
        #unique_together = ("student", "position")
        pass
    
    def get_fields(self):
        # make a list of field/values.
        k = []
        for field in Supervisor._meta.fields:
            if field.verbose_name == "ID" or field.name == "external":
                pass
            # TO DO: quick workaround to getting actual values displaying instead of ids
            # There's probably a more elegant way of doing this 
            elif field.name == "supervisor" or field.name == "student":
                nameOfPerson = ""
                #if field.name == "supervisor": 
                #    nameOfPerson = Person.objects.get(id=field.value_to_string(self))
                if field.name == "student":
                    nameOfPerson = GradStudent.objects.get(id=field.value_to_string(self))
                k.append([capfirst(field.verbose_name), nameOfPerson])
            else:
                k.append([capfirst(field.verbose_name), field.value_to_string(self) or None])
        return k        
    def __unicode__(self):
        return u"%s (%s) for %s" % (self.supervisor or self.external, self.supervisor_type, self.student.person)

    def save(self, *args, **kwargs):
        # make sure the data is coherent: should also be in form validation for nice UI
        is_person = bool(self.supervisor)
        is_ext = bool(self.external)
        if is_person and is_ext:
            raise ValueError, "Cannot be both an SFU user and external"
        if not is_person and not is_ext:
            raise ValueError, "Must be either an SFU user or external"
        
        if self.position == 1 and self.supervisor_type != 'SEN':
            raise ValueError, "First supervisor must be senior"
        #if self.position == 1 and is_ext:
        #    raise ValueError, "First supervisor must be internal"
        if self.position > 2 and self.supervisor_type == 'SEN':
            raise ValueError, "Only first two supervisors can be senior"
        
        if self.supervisor_type in ['SEN', 'COM'] and not (1 <= self.position  <= 4):
            raise ValueError, "Invalid position for committee member."
        
        if self.position > 0:
            others = Supervisor.objects.filter(student=self.student, position=self.position)
            if self.id:
                others = others.exclude(id=self.id)
            if others:
                raise ValueError, "Position (>0) must be unique"
        
        super(Supervisor, self).save(*args, **kwargs)

class GradRequirement(models.Model):
    """
    A requirement that a unit has for grad students
    """
    program = models.ForeignKey(GradProgram, null=False, blank=False)
    description = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    def __unicode__(self):
        return u"%s" % (self.description)    
        

class CompletedRequirement(models.Model):
    """
    A requirement met by a student (or notes about them meeting it in the future)
    """
    requirement = models.ForeignKey(GradRequirement)
    student = models.ForeignKey(GradStudent)
    semester = models.ForeignKey(Semester, null=False,
            help_text="Semester when the requirement was completed")
    date = models.DateField(null=True, blank=True,
            help_text="Date the requirement was completed (optional)")
    notes = models.TextField(null=True, blank=True, help_text="Other notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')    
    class meta:
        unique_together = (("requirement", "student"),)
    def __unicode__(self):
        return u"%s" % (self.requirement)

STATUS_CHOICES = (
        ('APPL', 'Applicant'),
        ('ACTI', 'Active'),
        ('PART', 'Part-Time'),
        ('LEAV', 'On-Leave'),
        ('WIDR', 'Withdrawn'),
        ('GRAD', 'Graduated'),
        ('NOND', 'Non-degree'),
        ('GONE', 'Gone'),
        ('ARSP', 'Completed Special'), # Special Arrangements and GONE
        )
STATUS_ACTIVE = ('ACTI', 'PART', 'NOND') # statuses that mean "still around"
STATUS_INACTIVE = ('LEAV', 'WIDR', 'GRAD', 'GONE', 'ARSP') # statuses that mean "not here"

class GradStatus(models.Model):
    """
    A "status" for a grad student: what were they doing in this range of semesters?
    """
    student = models.ForeignKey(GradStudent)
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, blank=False)
    start = models.ForeignKey(Semester, null=False, related_name="start_semester",
            help_text="First semester of this status")
    start_date = models.DateField(null=True, blank=True,
            help_text="Date the status began (optional)")
    end = models.ForeignKey(Semester, null=True, blank=True, related_name="end_semester",
            help_text="Final semester of this status: blank for ongoing")
    notes = models.TextField(blank=True, help_text="Other notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Set this flag if the status is no longer to be accessible.
    hidden = models.BooleanField(null=False, db_index=True, default=False)

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted, set the hidden flag instead."

    def save(self, close_others=True, *args, **kwargs):
        super(GradStatus, self).save(*args, **kwargs)

        # make sure any other statuses are closed
        if close_others:
            other_gs = GradStatus.objects.filter(student=self.student, end__isnull=True).exclude(id=self.id)
            for gs in other_gs:
                gs.end = max(self.start, gs.start)
                gs.save(close_others=False)
        
    def get_fields(self):
        # make a list of field/values.
        k = []
        for field in GradStatus._meta.fields:
                k.append([capfirst(field.verbose_name), field.value_to_string(self)])
        return k    
    
    def __unicode__(self):
        return u"Grad Status: %s %s" % (self.status, self.student)

"""
Letters
"""

class LetterTemplate(models.Model):
    unit = models.ForeignKey(Unit, null=False, blank=False)
    label = models.CharField(max_length=250, null=False)
        # likely choices: visa, international, msc offer, phd offer, special student offer, qualifying student offer
    content = models.TextField(help_text="I.e. 'This is to confirm {{title}} {{last_name}} ... '")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Letter template created by.')    

    def autoslug(self):
        return make_slug(self.unit.label + "-" + self.label)  
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False)
    class Meta:
        unique_together = ('unit', 'label')      
    def __unicode__(self):
        return u"%s in %s" % (self.label, self.unit)
    
class Letter(models.Model):
    student = models.ForeignKey(GradStudent, null=False, blank=False)
    date = models.DateField(help_text="The sending date of the letter")
    to_lines = models.TextField(help_text='Delivery address for the letter', null=True, blank=True)
    content = models.TextField(help_text="I.e. 'This is to confirm Mr. Baker ... '")
    template = models.ForeignKey(LetterTemplate)
    salutation = models.CharField(max_length=100, default="To whom it may concern")
    closing = models.CharField(max_length=100, default="Yours truly")
    from_person = models.ForeignKey(Person, null=True)
    from_lines = models.TextField(help_text='Name (and title) of the signer, e.g. "John Smith, Program Director"')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Letter generation requseted by.')
    config = JSONField(default={}) # addition configuration for within the letter
        # data returned by grad.letter_info() is stored here.

    def autoslug(self):
        return make_slug(self.student.slug + "-" + self.template.label)     
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)            
    def __unicode__(self):
        return u"%s letter for %s" % (self.template.label, self.student)

"""
Financial
"""

class ScholarshipType(models.Model):
    unit = models.ForeignKey(Unit)
    name = models.CharField(max_length=256)
    eligible = models.BooleanField(default=True, help_text="Does this scholarship count towards promises of support?")
    comments = models.TextField(blank=True, null=True)
    class meta:
        unique_together = ("unit", "name")
    def __unicode__(self):
        return u"%s - %s" % (self.unit.label, self.name)

class Scholarship(models.Model):
    scholarship_type = models.ForeignKey(ScholarshipType)
    student = models.ForeignKey(GradStudent)
    amount = models.DecimalField(verbose_name="Scholarship Amount", max_digits=8, decimal_places=2)
    start_semester = models.ForeignKey(Semester, related_name="scholarship_start")
    end_semester = models.ForeignKey(Semester, related_name="scholarship_end")
    comments = models.TextField(blank=True, null=True)
    def __unicode__(self):
        return u"%s (%s)" % (self.scholarship_type, self.amount)
    
    
class OtherFunding(models.Model):
    student = models.ForeignKey(GradStudent)
    semester = models.ForeignKey(Semester, related_name="other_funding")
    description = models.CharField(max_length=100, blank=False)
    amount = models.DecimalField(verbose_name="Funding Amount", max_digits=8, decimal_places=2)
    eligible = models.BooleanField()
    comments = models.TextField(blank=True, null=True)
    
class Promise(models.Model):
    student = models.ForeignKey(GradStudent)
    amount = models.DecimalField(verbose_name="Promise Amount", max_digits=8, decimal_places=2)
    start_semester = models.ForeignKey(Semester, related_name="promise_start")
    end_semester = models.ForeignKey(Semester, related_name="promise_end")
    comments = models.TextField(blank=True, null=True)
    def __unicode__(self):
        return u"%s promise for %s" % (self.amount, self.student.person)
    def get_fields(self):
        # make a list of field/values.
        k = []
        for field in Promise._meta.fields:
                k.append([capfirst(field.verbose_name), field.value_to_string(self)])
        return k

class SavedSearch(models.Model):
    person = models.ForeignKey(Person, null=True)
    query = models.TextField()
    config = JSONField(null=False, blank=False, default={})
    
    class Meta:
        #unique_together = (('person', 'query'),)
        pass
        
    defaults = {'name': ''}
    name, set_name = getter_setter('name')

