from django.db import models
from coredata.models import Person, Unit, Semester, CAMPUS_CHOICES
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from courselib.json_fields import getter_setter
from jsonfield import JSONField
from pages.models import _normalize_newlines
import re, itertools
many_newlines = re.compile(r'\n{3,}')

class GradProgram(models.Model):
    unit = models.ForeignKey(Unit, null=False, blank=False)
    label = models.CharField(max_length=20, null=False)
    description = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    created_by = models.CharField(max_length=32, null=False, help_text='Grad Program created by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Grad Program modified by.')
    hidden = models.BooleanField(null=False, default=False)
    def autoslug(self):
        # strip the punctutation entirely
        sluglabel = ''.join((c for c in self.label if c.isalnum()))
        return make_slug(sluglabel)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with=('unit',))
    class Meta:
        unique_together = (('unit', 'label'),)
    def __unicode__ (self):
        return u"%s" % (self.label)

STATUS_CHOICES = (
        ('INCO', 'Incomplete Application'),
        ('COMP', 'Complete Application'),
        ('INRE', 'Application In-Review'),
        ('HOLD', 'Hold Application'),
        ('OFFO', 'Offer Out'),
        ('REJE', 'Rejected Application'),
        ('DECL', 'Declined Offer'),
        ('EXPI', 'Expired Application'),
        ('CONF', 'Confirmed Acceptance'),
        ('CANC', 'Cancelled Acceptance'),
        ('ARIV', 'Arrived'),
        ('ACTI', 'Active'),
        ('PART', 'Part-Time'),
        ('LEAV', 'On-Leave'),
        ('WIDR', 'Withdrawn'),
        ('GRAD', 'Graduated'),
        ('NOND', 'Non-degree'),
        ('GONE', 'Gone'),
        ('ARSP', 'Completed Special'), # Special Arrangements and GONE
        )
STATUS_APPLICANT = ('INCO', 'COMP', 'INRE', 'HOLD', 'OFFO', 'REJE', 'DECL', 'EXPI', 'CONF', 'CANC', 'ARIV') # statuses that mean "applicant"
STATUS_ACTIVE = ('ACTI', 'PART', 'NOND') # statuses that mean "still around"
STATUS_DONE = ('WIDR', 'GRAD', 'GONE', 'ARSP') # statuses that mean "done"
STATUS_INACTIVE = ('LEAV',) + STATUS_DONE # statuses that mean "not here"

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    created_by = models.CharField(max_length=32, null=False, help_text='Grad Student created by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Grad Student modified by.', verbose_name='Last Modified By')
    
    # fields that are essentially denormalized caches for advanced search. Updated by self.update_status_fields()
    start_semester = models.ForeignKey(Semester, null=True, help_text="Semester when the student started the program.", related_name='grad_start_sem')
    end_semester = models.ForeignKey(Semester, null=True, help_text="Semester when the student finished/left the program.", related_name='grad_end_sem')
    current_status = models.CharField(max_length=4, null=True, choices=STATUS_CHOICES, help_text="Current student status")

    config = JSONField(default={}) # addition configuration
        # 'sin': Social Insurance Number
        # 'app_id': unique identifier for the PCS application import (so we can detect duplicate imports)
        # 'start_semester': first semester of project (if known from PCS import), as a semester.name (e.g. '1127')
    defaults = {'sin': '000000000'}
    sin, set_sin = getter_setter('sin')

    def __unicode__(self):
        return u"%s, %s" % (self.person, self.program.label)
    def save(self, *args, **kwargs):
        # rebuild slug in case something changes
        self.slug = None
        super(GradStudent, self).save(*args, **kwargs)

    def update_status_fields(self):
        """
        Update the self.start_semester, self.end_semester, self.current_status fields.
        """
        all_gs = GradStatus.objects.filter(student=self)
        old = (self.start_semester_id, self.end_semester_id, self.current_status)
        self.start_semester = None
        self.end_semester = None
        self.current_status = None
        
        # current_status
        last_status = list(all_gs.filter(end__isnull=True).order_by('-start__name')) \
                      + list(all_gs.order_by('-start__name', '-end__name'))
        if len(last_status) > 0:
            self.current_status = last_status[0].status
        
        # start_semester
        starts = all_gs.filter(status__in=STATUS_ACTIVE).order_by('start__name')
        if starts.count() > 0:
            start_status = starts[0]
            self.start_semester = start_status.start

        # end_semester
        ends = all_gs.filter(status__in=STATUS_DONE).order_by('-start__name')
        if ends.count() > 0:
            end_status = ends[0]
            self.end_semester = end_status.start
        
        if old != (self.start_semester_id, self.end_semester_id, self.current_status):
            self.save()
    
    def start_semester_guess(self):
        """
        Semester this student started, guessing if necessary
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
        """
        Context dictionary for building letter text
        """
        from ta.models import TAContract, TACourse, HOURS_PER_BU
        from ra.models import RAAppointment

        # basic personal stuff
        gender = self.person.gender()
        title = self.person.get_title()
        
        if gender == "M" :
            hisher = "his"
            heshe = 'he'
        elif gender == "F":
            hisher = "her"
            heshe = 'she'
        else:
            hisher = "his/her"
            heshe = 'he/she'
        
        # financial stuff
        promises = Promise.objects.filter(student=self).order_by('-start_semester')
        if promises:
            try:
                promise = "${:,f}".format(promises[0].amount)
            except ValueError: # handle Python <2.7
                promise = '$' + unicode(promises[0].amount)
        else:
            promise = u'$0'

        tas = TAContract.objects.filter(application__person=self.person).order_by('-posting__semester__name')
        ras = RAAppointment.objects.filter(person=self.person).order_by('-start_date')
        schols = Scholarship.objects.filter(student=self).order_by('start_semester__name').select_related('start_semester')
        if tas and ras:
            if tas[0].application.posting.semester.name > ras[0].start_semester().name:
                recent_empl = 'teaching assistant'
            else:
                recent_empl = 'research assistant'
        elif tas:
            recent_empl = 'teaching assistant'
        elif ras:
            recent_empl = 'research assistant'
        else:
            recent_empl = 'UNKNOWN'

        # TAing
        tafunding = ''
        tacourses = TACourse.objects.filter(contract__application__person=self.person) \
                    .order_by('contract__posting__semester__name') \
                    .select_related('contract__posting__semester', 'course')
        for tacrs in tacourses:
            tafunding += "||%s (%s)|%s %s|$%.2f|%i hours/term\n" % (
                    tacrs.contract.posting.semester.label(), tacrs.contract.posting.semester.months(),
                    tacrs.course.subject, tacrs.course.number,
                    tacrs.pay(), tacrs.bu*HOURS_PER_BU)
        
        # RAing
        rafunding = ''
        ras = list(ras)
        ras.reverse()
        for ra in ras:
            rafunding += "||%s-%s|$%.2f|%i hours/week\n" % (
                    ra.start_date.strftime("%b %Y"), ra.end_date.strftime("%b %Y"), ra.lump_sum_pay, ra.hours/2)
        
        # Scholarships
        scholarships = ''
        for s in schols:
            scholarships += "||%s (%s)|$%.2f|%s\n" % (
                        s.start_semester.label(), s.start_semester.months(),
                        s.amount, s.scholarship_type.name)

        # starting info
        startsem = self.start_semester_guess()
        if startsem:
            startyear = unicode(startsem.start.year)
            startsem = startsem.label()
        else:
            startyear = 'UNKNOWN'
            startsem = 'UNKNOWN'
        
        potentials = Supervisor.objects.filter(student=self, supervisor_type='POT', removed=False).exclude(supervisor__isnull=True)
        if potentials:
            potsup = potentials[0]
            supervisor_name = potsup.supervisor.name()
            supervisor_email = potsup.supervisor.email()
            sgender = potsup.supervisor.gender()
            if sgender == "M" :
                supervisor_hisher = "his"
                supervisor_heshe = "he"
            elif sgender == "F":
                supervisor_hisher = "her"
                supervisor_heshe = "she"
            else:
                supervisor_hisher = "his/her"
                supervisor_heshe = "he/she"
        else:
            supervisor_name = 'UNKNOWN'
            supervisor_email = 'UNKNOWN@sfu.ca'
            supervisor_hisher = 'his/her'
            supervisor_heshe = "he/she"
        
        ls = {
                'title' : title,
                'his_her' : hisher,
                'His_Her' : hisher.title(),
                'he_she' : heshe,
                'He_She' : heshe.title(),
                'first_name': self.person.first_name,
                'last_name': self.person.last_name,
                'promise': promise,
                'start_semester': startsem,
                'start_year': startyear,
                'program': self.program.description,
                'supervisor_name': supervisor_name,
                'supervisor_hisher': supervisor_hisher,
                'supervisor_heshe': supervisor_heshe,
                'supervisor_email': supervisor_email,
                'recent_empl': recent_empl,
                'tafunding': tafunding,
                'rafunding': rafunding,
                'scholarships': scholarships,
              }
        return ls

    def financials_from(self, start, end):
        """
        Return information about finances from the start to end semester. eligible_only: include only things ineligible for promises?
        
        Returns a data structure:
        {Semester: {
          'ta': [TACourse],
          'ra': [RAAppointment],
          'scholarship: [Scholarship],
          'other': [OtherFunding]
          }
        }
        Each of the objects in the lists are annotated with
          object.semlength: number of semesters this funding thing lasts for
          object.semvalue: the dollar amount for one semester
          object.promiseeligible: is eligible to count towards a promise?
        """
        from ta.models import TACourse
        from ra.models import RAAppointment
        
        semesters = {}
        for sem in Semester.objects.filter(name__gte=start.name, name__lte=end.name):
            semesters[sem] = {'ta': [], 'ra': [], 'scholarship': [], 'other': []}
        
        # TAs
        tas = TACourse.objects.filter(contract__application__person=self.person,
                                      contract__posting__semester__name__lte=end.name, contract__posting__semester__name__gte=start.name)
        for tacrs in tas:
            tacrs.semlength = 1
            tacrs.semvalue = tacrs.pay()
            tacrs.promiseeligible = True
            semesters[tacrs.contract.posting.semester]['ta'].append(tacrs)
        
        # RAs
        ras = RAAppointment.objects.filter(person=self.person)
        for ra in ras:
            # RAs are by date, not semester, so have to filter more here...
            st = ra.start_semester()
            en = ra.end_semester()
            ra.semlength = ra.semester_length()
            ra.semvalue = ra.lump_sum_pay / ra.semlength
            ra.promiseeligible = True
            sem = st
            while sem <= en:
                if sem in semesters:
                    semesters[sem]['ra'].append(ra)
                sem = sem.next_semester()
        
        # scholarships
        scholarships = Scholarship.objects.filter(student=self, start_semester__name__lte=end.name, end_semester__name__gte=start.name)
        for schol in scholarships:
            # annotate object with useful fields
            schol.semlength = schol.end_semester - schol.start_semester + 1
            schol.semvalue = schol.amount / schol.semlength
            schol.promiseeligible = schol.scholarship_type.eligible
            
            sem = schol.start_semester
            while sem <= schol.end_semester:
                if sem in semesters:
                    semesters[sem]['scholarship'].append(schol)
                sem = sem.next_semester()
        
        # other funding
        others = OtherFunding.objects.filter(student=self, semester__name__lte=end.name, semester__name__gte=start.name)
        for other in others:
            # annotate object with useful fields
            other.semlength = 1
            other.semvalue = other.amount
            other.promiseeligible = other.eligible
            semesters[sem]['other'].append(other)
            
        return semesters

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
               'he_she' : '"he" or "she" (or use He_She for capitalized)',
               'program': 'the program the student is enrolled in',
               'start_semester': 'student\'s first semester (e.g. "Summer 2000")',
               'start_year': 'year of student\'s first semester (e.g. "2000")',
               'promise': 'the amount of the [most recent] funding promise to the student (e.g. "$17,000")',
               'supervisor_name': "the name of the student's potential supervisor",
               'supervisor_hisher': 'pronoun for the potential supervisor ("his" or "her")',
               'supervisor_heshe': 'pronoun for the potential supervisor ("he" or "she")',
               'supervisor_email': "potential supervisor's email address",
               'recent_empl': 'most recent employment ("teaching assistant" or "research assistant")',
               'tafunding': 'List of funding as a TA',
               'rafunding': 'List of funding as an RA',
               'scholarships': 'List of scholarships received',
               }

SUPERVISOR_TYPE_CHOICES = [
    ('SEN', 'Senior Supervisor'),
    ('COM', 'Committee Member'),
    ('CHA', 'Defence Chair'),
    ('EXT', 'External Examiner'),
    ('SFU', 'SFU Examiner'),
    ('POT', 'Potential Supervisor'),
    ]
SUPERVISOR_TYPE_ORDER = {
    'SEN': 1,
    'COM': 2,
    'CHA': 3,
    'EXT': 4,
    'SFU': 5,
    'POT': 6,
    }

class Supervisor(models.Model):
    """
    Member (or potential member) of student's supervisory committee.
    """
    student = models.ForeignKey(GradStudent)
    supervisor = models.ForeignKey(Person, blank=True, null=True, verbose_name="Member")
    external = models.CharField(max_length=200, blank=True, null=True, help_text="Details if not an SFU internal member")
    #position = models.SmallIntegerField(null=False)
    #is_senior = models.BooleanField()
    #is_potential = models.BooleanField()
    supervisor_type = models.CharField(max_length=3, blank=False, null=False, choices=SUPERVISOR_TYPE_CHOICES)
    removed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    created_by = models.CharField(max_length=32, null=False, help_text='Committee member added by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Committee member modified by.', verbose_name='Last Modified By')
    config = JSONField(default={}) # addition configuration
        # 'email': Email address (for external)
    defaults = {'email': None}
    email, set_email = getter_setter('email')
          
    class Meta:
        #unique_together = ("student", "position")
        pass
    
    def __unicode__(self):
        return u"%s (%s) for %s" % (self.supervisor or self.external, self.supervisor_type, self.student.person)

    def sortname(self):
        if self.supervisor:
            return self.supervisor.sortname()
        else:
            return self.external

    def save(self, *args, **kwargs):
        # make sure the data is coherent: should also be in form validation for nice UI
        is_person = bool(self.supervisor)
        is_ext = bool(self.external)
        if is_person and is_ext:
            raise ValueError, "Cannot be both an SFU user and external"
        if not is_person and not is_ext:
            raise ValueError, "Must be either an SFU user or external"
        
        super(Supervisor, self).save(*args, **kwargs)
    
    def type_order(self):
        "Return key for sorting by supervisor_type"
        return SUPERVISOR_TYPE_ORDER[self.supervisor_type]

class GradRequirement(models.Model):
    """
    A requirement that a unit has for grad students
    """
    program = models.ForeignKey(GradProgram, null=False, blank=False)
    description = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    hidden = models.BooleanField(default=False)
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
    removed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')    
    #class meta:
    #    unique_together = (("requirement", "student"),)
    def __unicode__(self):
        return u"%s" % (self.requirement)


STATUS_ORDER = {
        'INCO': 0,
        'COMP': 0,
        'INRE': 1,
        'HOLD': 1,
        'OFFO': 2,
        'REJE': 3,
        'DECL': 3,
        'EXPI': 3,
        'CONF': 4,
        'CANC': 5,
        'ARIV': 5,
        'APPL': 5,
        'ACTI': 6,
        'PART': 6,
        'LEAV': 7,
        'NOND': 7,
        'WIDR': 8,
        'GRAD': 8,
        'GONE': 8,
        'ARSP': 8,
        }
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

        if close_others:
            # update gradstudent status fields
            self.student.update_status_fields()

            # make sure any other statuses are closed
            other_gs = GradStatus.objects.filter(student=self.student, end__isnull=True).exclude(id=self.id)
            for gs in other_gs:
                gs.end = max(self.start, gs.start)
                gs.save(close_others=False)  
    
    def __unicode__(self):
        return u"Grad Status: %s %s" % (self.status, self.student)
    
    def status_order(self):
        "For sorting by status"
        return STATUS_ORDER[self.status]

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
    hidden = models.BooleanField(default=False)

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
    def save(self, *args, **kwargs):
        # normalize text so it's easy to work with
        if not self.to_lines:
            self.to_lines = ''
        _normalize_newlines(self.to_lines.rstrip())
        self.from_lines = _normalize_newlines(self.from_lines.rstrip())
        self.content = _normalize_newlines(self.content.rstrip())
        self.content = many_newlines.sub('\n\n', self.content)
        super(Letter, self).save(*args, **kwargs)

"""
Financial
"""

class ScholarshipType(models.Model):
    unit = models.ForeignKey(Unit)
    name = models.CharField(max_length=256)
    eligible = models.BooleanField(default=True, help_text="Does this scholarship count towards promises of support?")
    comments = models.TextField(blank=True, null=True)
    hidden = models.BooleanField(default=False)
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
    removed = models.BooleanField(default=False)
    def __unicode__(self):
        return u"%s (%s)" % (self.scholarship_type, self.amount)
    
    
class OtherFunding(models.Model):
    student = models.ForeignKey(GradStudent)
    semester = models.ForeignKey(Semester, related_name="other_funding")
    description = models.CharField(max_length=100, blank=False)
    amount = models.DecimalField(verbose_name="Funding Amount", max_digits=8, decimal_places=2)
    eligible = models.BooleanField(default=True, help_text="Does this funding count towards promises of support?")
    comments = models.TextField(blank=True, null=True)
    removed = models.BooleanField(default=False)
    
class Promise(models.Model):
    student = models.ForeignKey(GradStudent)
    amount = models.DecimalField(verbose_name="Promise Amount", max_digits=8, decimal_places=2)
    start_semester = models.ForeignKey(Semester, related_name="promise_start")
    end_semester = models.ForeignKey(Semester, related_name="promise_end")
    comments = models.TextField(blank=True, null=True)
    removed = models.BooleanField(default=False)
    def __unicode__(self):
        return u"%s promise for %s %s-%s" % (self.amount, self.student.person, self.start_semester.name, self.end_semester.name)

    def semester_length(self):
        return self.end_semester - self.start_semester + 1

    def contributions_to(self):
        """
        Find all funding that contributes to fulfilling this promise (includes ineligible ones)
        """
        # cache so we don't recalculate
        if not hasattr(self, '_contributions_cache'):
            self._contributions_cache = self.student.financials_from(start=self.start_semester, end=self.end_semester)
        return self._contributions_cache

    def received(self):
        """
        Amount actually received towards this promise
        """
        # cache so we don't recalculate
        if not hasattr(self, '_received_cache'):
            funding = self.contributions_to()
            funding_values = itertools.chain(*(
                        (
                            f.semvalue for f in itertools.chain(*               # value of each element
                                (funding[sem][ftype] for ftype in funding[sem]) # all funding elements
                            ) if f.promiseeligible
                        )
                        for sem in funding
                    ))
            self._received_cache = sum(funding_values)
        return self._received_cache

    def short(self):
        """
        How much are we short on this promise?
        """
        return self.amount - self.received()


class SavedSearch(models.Model):
    person = models.ForeignKey(Person, null=True)
    query = models.TextField()
    config = JSONField(null=False, blank=False, default={})
    
    class Meta:
        #unique_together = (('person', 'query'),)
        pass
        
    defaults = {'name': ''}
    name, set_name = getter_setter('name')

