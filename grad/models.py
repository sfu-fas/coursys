from django.db import models
from django.core.cache import cache
from coredata.models import Person, Unit, Semester, CAMPUS_CHOICES, Member
from autoslug import AutoSlugField
from cache_utils.decorators import cached
from courselib.slugs import make_slug
from courselib.json_fields import getter_setter
from courselib.json_fields import JSONField, config_property
from courselib.text import normalize_newlines, many_newlines
from courselib.conditional_save import ConditionalSaveMixin
from courselib.storage import UploadedFileStorage, upload_path
import itertools, datetime, os, uuid
import coredata.queries
from django.conf import settings
import django.db.transaction


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
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with=('unit',))
    class Meta:
        unique_together = (('unit', 'label'),)
    def __unicode__ (self):
        return u"%s" % (self.label)
    
    def cmpt_program_type(self):
        """
        REJEck for CMPT progress reports system export.
        """
        if self.label == 'MSc Course':
            return ('MSc', 'Course')
        elif self.label == 'MSc Proj':
            return ('MSc', 'Project')
        elif self.label == 'MSc Thesis':
            return ('MSc', 'Thesis')
        elif self.label == 'PhD':
            return ('PhD', 'Thesis')
        elif self.label == 'Qualifying':
            return ('Qualifying', '')
        elif self.label == 'Special':
            return ('Special', '')
        else:
            return ('???', '???')

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
        ('ARSP', 'Completed Special'), # Special Arrangements + GONE
        ('TRIN', 'Transferred from another department'),
        ('TROU', 'Transferred to another department'),
        ('DELE', 'Deleted Record'), # used to flag GradStudents as deleted
        ('DEFR', 'Deferred'),
        ('GAPL', 'Applied for Graduation'),
        ('GAPR', 'Graduation Approved'),
        )
STATUS_APPLICANT = ('APPL', 'INCO', 'COMP', 'INRE', 'HOLD', 'OFFO', 'REJE', 'DECL', 'EXPI', 'CONF', 'CANC', 'ARIV',
                    'DEFR') # statuses that mean "applicant"
STATUS_CURRENTAPPLICANT = ('INCO', 'COMP', 'INRE', 'HOLD', 'OFFO') # statuses that mean "currently applying"
STATUS_ACTIVE = ('ACTI', 'PART', 'NOND') # statuses that mean "still around"
STATUS_GPA = ('GAPL', 'GAPR',) + STATUS_ACTIVE  # Statuses for which we want to import the GPA
STATUS_DONE = ('WIDR', 'GRAD', 'GONE', 'ARSP', 'GAPL', 'GAPR') # statuses that mean "done"
STATUS_INACTIVE = ('LEAV',) + STATUS_DONE # statuses that mean "not here"
STATUS_OBSOLETE = ('APPL', 'INCO', 'REFU', 'INRE', 'ARIV', 'GONE', 'DELE', 'TRIN', 'TROU') # statuses we don't let users enter
STATUS_REAL_PROGRAM = STATUS_CURRENTAPPLICANT + STATUS_ACTIVE + STATUS_INACTIVE # things to report for TAs
SHORT_STATUSES = dict([  # a shorter status description we can use in compact tables
        ('INCO', 'Incomp App'),
        ('COMP', 'Complete App'),
        ('INRE', 'In-Review'),
        ('HOLD', 'Hold'),
        ('OFFO', 'Offer'),
        ('REJE', 'Reject'),
        ('DECL', 'Declined'),
        ('EXPI', 'Expired'),
        ('CONF', 'Confirmed'),
        ('CANC', 'Cancelled'),
        ('ARIV', 'Arrive'),
        ('ACTI', 'Active'),
        ('PART', 'Part-Time'),
        ('LEAV', 'On-Leave'),
        ('WIDR', 'Withdrawn'),
        ('GRAD', 'Grad'),
        ('NOND', 'Non-deg'),
        ('GONE', 'Gone'),
        ('ARSP', 'Completed'), # Special Arrangements + GONE
        ('TRIN', 'Transfer in'),
        ('TROU', 'Transfer out'),
        ('DELE', 'Deleted Record'),
        ('DEFR', 'Deferred'),
        ('GAPL', 'Grad Applied'),
        ('GAPR', 'Grad Approved'),
        (None, 'None'),
])

GRAD_CAMPUS_CHOICES = CAMPUS_CHOICES + (('MULTI', 'Multiple Campuses'),)

THESIS_TYPE_CHOICES = (
    ('T','Thesis'), 
    ('P','Project'), 
    ('E','Extended Essay'))

THESIS_OUTCOME_CHOICES = (
    ('NONE', "None (No Outcome)"),
    ('PASS', "Pass (No Changes)"),
    ('MINR', "Pass (Minor Changes)"),
    ('DEFR', "Defer (Major Changes)"),
    ('FAIL', "Fail"))

PROGRESS_REPORT_CHOICES = (
    ('GOOD', "Good"),
    ('SATI', "Satisfactory"),
    ('CONC', "Satisfactory with Concerns"),
    ('UNST',  "Unsatisfactory"))

# floated out here to allow caching by pk
@cached(24*3600)
def _active_semesters(pk, program=None):
    self = GradStudent.objects.get(pk=pk)
    next_sem = Semester.current().offset(1)
    if program:
        start = program.start_semester
    else:
        start = self.start_semester or next_sem
    end = self.end_semester or next_sem

    statuses_that_indicate_a_change_in_state = STATUS_ACTIVE + STATUS_INACTIVE
    statuses = GradStatus.objects.filter(student=self, hidden=False, status__in=statuses_that_indicate_a_change_in_state) \
               .order_by('start__name', 'start_date', 'created_at') \
               .select_related('start')

    statuses = list(statuses)
    sem = start
    active = 0
    total = 0
    while sem.name < end.name:
        prev_statuses = [st for st in statuses if st.start.name <= sem.name]
        if prev_statuses:
            this_status = prev_statuses[-1]
            if this_status.status in STATUS_ACTIVE:
                active += 1
                total += 1
            elif this_status.status in STATUS_INACTIVE and this_status.status not in STATUS_DONE:
                total += 1
        sem = sem.next_semester()

    return active, total

@cached(24*3600)
def _active_semesters_display(pk):
    self = GradStudent.objects.get(pk=pk)
    active, total = self.active_semesters()
    res = u"%i/%i" % (active, total)

    history = GradProgramHistory.objects.filter(student=self).order_by('-starting', '-start_semester').select_related('program')
    if history.count() > 1:
        currentprog = history.first()
        active, total = self.active_semesters(program=currentprog)
        res += ' (%i/%i in %s)' % (active, total, currentprog.program.label)

    return res


@cached(24*3600)
def _program_start_end_semesters_display(pk):
    self = GradStudent.objects.get(pk=pk)
    start = self.start_semester.name if self.start_semester else "???"
    end = self.end_semester.name if self.end_semester else "present"
    history = GradProgramHistory.objects.filter(student=self).order_by('-starting', '-start_semester').select_related(
        'program')
    res = u"%s - %s" % (start, end)
    if history.count() > 1:
        currentprog = history.first()
        if not currentprog.start_semester == self.start_semester:
            res += ' (%s start semester: %s)' % (currentprog.program.label, currentprog.start_semester.name)
    return res


class GradStudentManager(models.Manager):
    # never return deleted GradStudent objects
    def get_queryset(self):
        qs = super(GradStudentManager, self).get_queryset()
        #qs = qs.filter(config__contains='sims_source')
        qs = qs.exclude(current_status='DELE')
        return qs


class GradStudent(models.Model, ConditionalSaveMixin):
    """
    Represents one grad student "career".

    (...within a single unit: transfers between units get multiple GradStudent objects so staff in each unit can see
    the data they should, but not the rest.)
    """
    objects = GradStudentManager()
    all_objects = models.Manager()

    person = models.ForeignKey(Person, help_text="Type in student ID or number.", null=False, blank=False, unique=False)
    program = models.ForeignKey(GradProgram, null=False, blank=False)
    def autoslug(self):
        if self.person.userid:
            userid = self.person.userid
        else:
            userid = str(self.person.emplid)
        return make_slug(userid + "-" + self.program.slug)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True, manager=all_objects)
    research_area = models.TextField('Research Area', blank=True)
    campus = models.CharField(max_length=5, choices=GRAD_CAMPUS_CHOICES, blank=True, db_index=True)

    english_fluency = models.CharField(max_length=50, blank=True, help_text="I.e. Read, Write, Speak, All.")
    mother_tongue = models.CharField(max_length=25, blank=True, help_text="I.e. English, Chinese, French")
    is_canadian = models.NullBooleanField()
    passport_issued_by = models.CharField(max_length=30, blank=True, help_text="I.e. US, China")
    comments = models.TextField(max_length=250, blank=True, help_text="Additional information.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    created_by = models.CharField(max_length=32, null=False, help_text='Grad Student created by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Grad Student modified by.', verbose_name='Last Modified By')
    
    # fields that are essentially denormalized caches for advanced search. Updated by self.update_status_fields()
    start_semester = models.ForeignKey(Semester, null=True, help_text="Semester when the student started the program.", related_name='grad_start_sem')
    end_semester = models.ForeignKey(Semester, null=True, help_text="Semester when the student finished/left the program.", related_name='grad_end_sem')
    current_status = models.CharField(max_length=4, null=True, choices=STATUS_CHOICES, help_text="Current student status", db_index=True)

    config = JSONField(default=dict) # addition configuration
        # 'sin': Social Insurance Number: no longer used. Now at self.person.sin()
        # 'app_id': unique identifier for the PCS application import (so we can detect duplicate imports)
        # 'start_semester': first semester of project (if known from PCS import), as a semester.name (e.g. '1127')
        # 'thesis_type': 'T'/'P'/'E' for Thesis/Project/Extended Essay
        # 'work_title': title of the Thesis/Project/Extended Essay
        # 'exam_date': date of the Thesis/Project/Extended Essay
        # 'applic_email': email address from the application process (where it could be imported)
        # 'start_semester': manually-set value to override the guess made by update_status_fields(). A semester.name (e.g. '1127') or None.
        # 'end_semester': manually-set value to override the guess made by update_status_fields(). A semester.name (e.g. '1127') or None.
        # -- added for Engineering --
        # 'thesis_outcome': outcome of Thesis/Project/Extended Essay
        # 'thesis_location': location of thesis exam
        # 'qualifying_exam_date': date of qualifying exam
        # 'qualifying_exam_location': location of qualifying exam 
        # 'place_of_birth': place of birth of the grad student
        # 'bachelors_cgpa' : as a string
        # 'masters_cgpa' : as a string
        # 'progress': Progress on M.Eng, Ph.D, or MASc.

    defaults = {'sin': '000000000', 'applic_email': None, 
        'exam_location':'',
        'place_of_birth':'', 
        'bachelors_cgpa':'', 
        'masters_cgpa':'',
        'qualifying_exam_date':'',
        'qualifying_exam_location':'',
        'progress':'',
        'notes':''}

    #sin, set_sin = getter_setter('sin')
    applic_email, set_applic_email = getter_setter('applic_email')
    notes, set_notes = getter_setter('notes')
    
    tacked_on_fields = [
        ('place_of_birth', "Place of Birth"),
        ('bachelors_cgpa', "Bachelors' CGPA"),
        ('masters_cgpa', "Masters' CGPA"),
        ('progress', "Last Progress Report"),
        ('qualifying_exam_date', "Date of qualifying exam"),
        ('qualifying_exam_location', "Location of qualifying exam"),
    ]


    def __unicode__(self):
        return u"%s, %s" % (self.person, self.program.label)

    def save(self, *args, **kwargs):
        # rebuild slug in case something changes
        self.slug = None

        super(GradStudent, self).save(*args, **kwargs)

    def status_as_of(self, semester=None):
        """ Like 'current status', but for an arbitrary semester.

            We want to filter out any statuses that occur after the  semester,
            because - if a student is active this semester (assuming that we are 1134)
            and on-leave next semester (1137) their current status is active.

            Active statuses have precedence over Applicant statuses.
            if a student is Active in 1134 but Complete Application in 1137, they are Active.
        """
        if self.current_status == 'DELE':
            raise ValueError

        if semester == None:
            semester = Semester.current()

        timely_status = models.Q(start__name__lte=semester.name)
        application_status = models.Q(start__name__lte=semester.offset_name(3), status__in=STATUS_APPLICANT)

        statuses = GradStatus.objects.filter(student=self, hidden=False) \
                    .filter(timely_status | application_status) \
                    .order_by('-start__name', '-start_date').select_related('start')

        # Only keep the statuses that don't have the ignore_status flag set, which should be all of them in almost all
        # cases, as the flag was introduced for a particular edge case.

        statuses = [s for s in statuses if not s.ignore_status]

        if not statuses:
            return None

        # find all statuses in the most-recent semester: the one that sorts last wins.
        status_sem = statuses[0].start

        semester_statuses = [(
                                 st.start.name,
                                 st.start_date or st.created_at.date() or datetime.date(1970, 1, 1),
                                 st)
                             for st in statuses if st.start == status_sem]
        semester_statuses.sort()
        return semester_statuses[-1][2].status


    def status_as_of_old(self, semester=None):
        """ Like 'current status', but for an arbitrary semester. 
        
            We want to filter out any statuses that occur after the  semester,
            because - if a student is active this semester (assuming that we are 1134)
            and on-leave next semester (1137) their current status is active.
            
            However, if their status is Rejected Application in 1137, their current 
            status is "Rejected", even if 1137 hasn't happened yet - but, if their
            Rejected status was created after the semester that we are asking about (1134),
            then we should return None. 

            Active statuses have precedence over Applicant statuses.
            if a student is Active in 1134 but Complete Application in 1137, they are Active. 
        """

        filter_future_statuses = True
        if semester == None:
            semester = Semester.current()
            filter_future_statuses = False

        all_gs = GradStatus.objects.filter(student=self, hidden=False).order_by('start')
        all_gs_by_date = GradStatus.objects.filter(student=self, hidden=False).order_by('start_date')

        filtered_nonapplicant_statuses = [status for status in all_gs if 
                status.start <= semester
                and status.status not in STATUS_APPLICANT ]
        filtered_applicant_statuses = [status for status in all_gs_by_date if
                status.status in STATUS_APPLICANT 
                and filter_future_statuses == False 
                or (status.start_date and status.start_date <= semester.end) ]
        if len(filtered_nonapplicant_statuses) > 0:
            return filtered_nonapplicant_statuses[-1].status
        elif len(filtered_applicant_statuses) > 0:
            return filtered_applicant_statuses[-1].status
        else:
            return None


    def update_status_fields(self):
        """
        Update the self.start_semester, self.end_semester, self.current_status, self.program fields.

        Called by updates to statuses, and also by grad.tasks.update_statuses_to_current to reflect future statuses
        when the future actually comes.
        """
        if self.current_status == 'DELE':
            raise ValueError
        old = (self.start_semester_id, self.end_semester_id, self.current_status, self.program_id)
        self.start_semester = None
        self.end_semester = None
        self.current_status = None

        # status and program
        self.current_status = self.status_as_of()
        prog = self.program_as_of(future_if_necessary=True)
        if prog:
            self.program = prog

        all_gs = GradStatus.objects.filter(student=self, hidden=False).order_by('start')

        # start_semester
        if 'start_semester' in self.config:
            if self.config['start_semester']:
                self.start_semester = Semester.objects.get(name=self.config['start_semester'])
            else:
                self.start_semester = None
        else:
            # take the EARLIEST ACTIVE GRADSTATUS 
            # then the LATEST CONFIRMED
            # then the LATEST OFFERED
            # finally the LATEST APPLICATION
            # if none of those, then no start_semester could be found. 

            active_statuses = [status for status in all_gs if status.status=='ACTI']
            confirmed_statuses = [status for status in all_gs if status.status=='CONF']
            offered_statuses = [status for status in all_gs if status.status=='OFFO']
            completed_application_statuses = [status for status in all_gs if status.status=='COMP']
            rejected_application_statuses = [status for status in all_gs if status.status=='REJE']

            if len(active_statuses) > 0:
                self.start_semester = active_statuses[0].start
            elif len(confirmed_statuses) > 0:
                self.start_semester = confirmed_statuses[-1].start
            elif len(offered_statuses) > 0:
                self.start_semester = offered_statuses[-1].start
            elif len(completed_application_statuses) > 0:
                self.start_semester = completed_application_statuses[-1].start
            elif len(rejected_application_statuses) > 0:
                self.start_semester = rejected_application_statuses[-1].start

        # end_semester
        # Modified to ignore the cases where people had 'end_semester': None in their config.
        if 'end_semester' in self.config and self.config['end_semester']:
                self.end_semester = Semester.objects.get(name=self.config['end_semester'])
        else:
            if self.current_status in STATUS_DONE:
                ends = [status for status in all_gs if status.status in STATUS_DONE]
                if len(ends) > 0:
                    end_status = ends[-1]
                    self.end_semester = end_status.start
            else:
                self.end_semester = None

        current = (self.start_semester_id, self.end_semester_id, self.current_status, self.program_id)
        if old != current:
            self.save()
            _active_semesters.invalidate(self.pk)
            _active_semesters_display.invalidate(self.pk)
            _program_start_end_semesters_display.invalidate(self.pk)


    def active_semesters(self, program=None):
        """
        Number of active and total semesters.

        If present, program should be a GradProgramHistory object for the program we're interested in: will return the
        number of semesters since the start of that program.

        Cache is invalidated by self.update_status_fields.
        """
        # actually flips through every relevant semester and checks to see
        # their (final) status in that semester. The data is messy enough
        # that I don't see any better way.
        return _active_semesters(self.pk, program)

    def _has_committee(self):
        senior_sups = Supervisor.objects.filter(student=self, supervisor_type='SEN', removed=False).count()
        return senior_sups > 0
    def clear_has_committee(self):
        key = 'has_committee-%i' % (self.id)
        cache.delete(key)
        
    def has_committee(self):
        """
        Does the student appear to have (some of) their committee formed?
        
        Used frequently in permission checking, so caching it.
        """
        key = 'has_committee-%i' % (self.id)
        res = cache.get(key)
        if res is None:
            res = self._has_committee()
            cache.set(key, res)

        return bool(res)

    def active_semesters_display(self):
        """
        Format self.active_semesters_display for display

        Cache is invalidated by self.update_status_fields.
        """
        return _active_semesters_display(self.pk)

    def program_start_end_semesters_display(self):
        """
        Format the start/end semesters including the current program ones if they are different than the
        GradStudent ones, which can happen in the case of program changes within the same career.

        Cache is invalidated by self.update_status_fields.
        """
        return _program_start_end_semesters_display(self.pk)


    def program_as_of(self, semester=None, future_if_necessary=False):
        if semester == None:
            semester = Semester.current()

        gph = GradProgramHistory.objects.filter(student=self, start_semester__name__lte=semester.name) \
            .order_by('-start_semester', '-starting').select_related('program').first()

        if not gph and future_if_necessary:
            # look into the future for the program the *will* be in: that's how we'll set gs.program earlier.
            gph = GradProgramHistory.objects.filter(student=self) \
            .order_by('start_semester', '-starting').select_related('program').first()

        if gph:
            return gph.program
        else:
            return None

    def flags_and_values(self):
        """
        Pairs fo GradFlag objects and GradFlagValue objects for this student
        """
        flags = GradFlag.objects.filter(unit=self.program.unit)
        values = GradFlagValue.objects.filter(student=self, flag__unit=self.program.unit)
        valuedict = dict(((v.flag, v) for v in values))
        
        for f in flags:
            if f in valuedict:
                yield (f, valuedict[f])
            else:
                v = GradFlagValue(student=self, flag=f)
                #v.save()
                yield (f, v)
        
    def status_order(self):
        "For sorting by status"
        return STATUS_ORDER[self.current_status]
    def get_short_current_status_display(self):
        return SHORT_STATUSES[self.current_status]

    def sessional_courses(self):
        """
        Find courses this student taught, presumably as a sessional instructor. Returns relevant coredata.models.CourseOffering objects.
        """
        members = Member.objects.filter(person=self.person, role='INST', offering__graded=True).select_related('offering__owner')
        return [m.offering for m in members]
        
    def letter_info(self):
        """
        Context dictionary for building letter text
        """
        from ta.models import TAContract, TACourse, HOURS_PER_BU
        from ra.models import RAAppointment
        
        todays_date = datetime.date.today()

        # basic personal stuff
        emplid = self.person.emplid
        gender = self.person.gender()
        title = self.person.get_title()
        
        if gender == "M" :
            hisher = "his"
            heshe = 'he'
            himher = 'her'
        elif gender == "F":
            hisher = "her"
            heshe = 'she'
            himher = 'her'
        else:
            hisher = "his/her"
            heshe = 'he/she'
            himher = 'him/her'
        
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
        ras = RAAppointment.objects.filter(person=self.person, deleted=False).order_by('-start_date')
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

        last_ta_start_date = "?"
        last_ta_end_date = "?"
        last_ta_total_salary = "$?"
        if tas:
            last_ta = tas[0]
            last_ta_start_date = last_ta.pay_start
            last_ta_end_date = last_ta.pay_end
            last_ta_total_salary = "$%.2f" % last_ta.total_pay()
        
        # RAing
        rafunding = ''
        ras = list(ras)
        ras.reverse()
        for ra in ras:
            rafunding += "||%s-%s|$%.2f|%i hours/week\n" % (
                    ra.start_date.strftime("%b %Y"), ra.end_date.strftime("%b %Y"), ra.lump_sum_pay, ra.hours/2)

        last_ra_start_date = "?"
        last_ra_end_date = "?"
        last_ra_total_salary = "$?"
        last_ra_biweekly_salary = "$?"
        if ras:
            last_ra = ras[0]
            last_ra_start_date = last_ra.start_date
            last_ra_end_date = last_ra.end_date
            last_ra_total_salary = "$%.2f" % last_ra.lump_sum_pay
            last_ra_biweekly_salary = "$%.2f" % last_ra.biweekly_pay
        
        # Scholarships
        scholarships = ''
        for s in schols:
            scholarships += "||%s (%s)|$%.2f|%s\n" % (
                        s.start_semester.label(), s.start_semester.months(),
                        s.amount, s.scholarship_type.name)

        # starting info
        startsem = self.start_semester
        if startsem:
            startyear = unicode(startsem.start.year)
            startsem = startsem.label()
        else:
            startyear = 'UNKNOWN'
            startsem = 'UNKNOWN'
       
        def supervisor_details( supervisor_type, ordinal=1 ):
            # we default to selecting the first (ordinal=1) supervisor that matches the type
            # if ordinal > 1, we select the 2nd, 3rd, et-al
            supervisor_name = '?'
            supervisor_email = '?'
            supervisor_hisher = 'his/her'
            supervisor_heshe = "he/she"
            supervisor_himher = "him/her"
            potentials = Supervisor.objects.filter(student=self, supervisor_type=supervisor_type, removed=False)
            if len(potentials) > ordinal-1:
                potsup = potentials[ordinal-1]
                if potsup.supervisor:
                    supervisor_name = potsup.supervisor.name()
                    supervisor_email = potsup.supervisor.email()
                    sgender = potsup.supervisor.gender()
                    if sgender == "M" :
                        supervisor_hisher = "his"
                        supervisor_heshe = "he"
                        supervisor_himher = "him"
                    elif sgender == "F":
                        supervisor_hisher = "her"
                        supervisor_heshe = "she"
                        supervisor_himher = "her"
                else:
                    supervisor_name = potsup.external
                    supervisor_email = ""
            return supervisor_name, supervisor_email, supervisor_hisher, supervisor_heshe, supervisor_himher
        
        supervisor_name, supervisor_email, supervisor_hisher, supervisor_heshe, supervisor_himher = supervisor_details("POT")
        sr_supervisor_name, sr_supervisor_email, sr_supervisor_hisher, sr_supervisor_heshe, sr_supervisor_himher = supervisor_details("SEN")
        defence_chair_name, defence_chair_email, x, y, z = supervisor_details('CHA')
        sfu_examiner_name, sfu_examiner_email, x, y, z = supervisor_details('SFU')
        external_examiner_name, external_examiner_email, x, y, z = supervisor_details('EXT')
        co_sr_supervisor_name, co_sr_supervisor_email, x, y, z = supervisor_details('COS')
        committee_1_name, committee_1_email, x, y, z = supervisor_details('COM', 1)
        committee_2_name, committee_2_email, x, y, z = supervisor_details('COM', 2)
        committee_3_name, committee_3_email, x, y, z = supervisor_details('COM', 3)

        all_supervisors = [x for x in Supervisor.objects.filter(student=self, removed=False)]
        all_supervisors.sort(cmp=lambda x,y: cmp(x.type_order(), y.type_order()))
        committee = ""
        for supervisor in all_supervisors:
            if supervisor.supervisor:
                name = supervisor.supervisor.name()
            else:
                name = supervisor.external
            committee += supervisor.get_supervisor_type_display() + ": " + name + "\n"

        sin = self.person.sin() 
        
        def config_or_unknown(key):
            if key in self.config:
                return self.config[key]
            else:
                return "?"
        
        thesis_title = config_or_unknown("work_title")
        thesis_date = config_or_unknown("exam_date")
        thesis_location = config_or_unknown("thesis_location")
        research_area = self.research_area
        
        qualifying_exam_date = config_or_unknown("qualifying_exam_date")
        qualifying_exam_location = config_or_unknown("qualifying_exam_location")

        ls = { # if changing, also update LETTER_TAGS below with docs!
               # For security reasons, all values must be strings (to avoid presenting dangerous methods in templates)
                'todays_date' : todays_date, 
                'title' : title,
                'his_her' : hisher,
                'His_Her' : hisher.title(),
                'he_she' : heshe,
                'He_She' : heshe.title(),
                'him_her' : himher,
                'Him_Her' : himher.title(),
                'first_name': self.person.first_name,
                'last_name': self.person.last_name,
                'emplid': emplid, 
                'promise': promise,
                'start_semester': startsem,
                'start_year': startyear,
                'program': self.program.description,
                'supervisor_name': supervisor_name,
                'supervisor_hisher': supervisor_hisher,
                'supervisor_heshe': supervisor_heshe,
                'supervisor_himher': supervisor_himher,
                'supervisor_email': supervisor_email,
                'committee': committee,
                'sr_supervisor_name': sr_supervisor_name,
                'sr_supervisor_hisher': sr_supervisor_hisher,
                'sr_supervisor_heshe': sr_supervisor_heshe,
                'sr_supervisor_himher': sr_supervisor_himher,
                'sr_supervisor_email': sr_supervisor_email,
                'defence_chair_name': defence_chair_name, 
                'defence_chair_email': defence_chair_email,
                'sfu_examiner_name': sfu_examiner_name, 
                'sfu_examiner_email': sfu_examiner_email,
                'external_examiner_name': external_examiner_name, 
                'external_examiner_email': external_examiner_email,
                'co_sr_supervisor_name': co_sr_supervisor_name, 
                'co_sr_supervisor_email': co_sr_supervisor_email,
                'committee_1_name': committee_1_name,
                'committee_1_email': committee_1_email, 
                'committee_2_name': committee_2_name,
                'committee_2_email': committee_2_email, 
                'committee_3_name': committee_3_name,
                'committee_3_email': committee_3_email, 
                'recent_empl': recent_empl,
                'tafunding': tafunding,
                'last_ta_start_date': last_ta_start_date, 
                'last_ta_end_date': last_ta_end_date, 
                'last_ta_total_salary': last_ta_total_salary, 
                'rafunding': rafunding,
                'last_ra_start_date': last_ra_start_date, 
                'last_ra_end_date': last_ra_end_date, 
                'last_ra_total_salary': last_ra_total_salary, 
                'last_ra_biweekly_salary': last_ra_biweekly_salary,
                'scholarships': scholarships,
                'sin':sin, 
                'thesis_title':thesis_title, 
                'thesis_date':thesis_date,
                'thesis_location':thesis_location,
                'research_area':research_area,
                'qualifying_exam_date':qualifying_exam_date,
                'qualifying_exam_location':qualifying_exam_location
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
        ras = RAAppointment.objects.filter(person=self.person, deleted=False)
        for ra in ras:
            # RAs are by date, not semester, so have to filter more here...
            st = ra.start_semester()
            en = ra.end_semester()
            ra.semlength = ra.semester_length()
            if ra.semlength == 0:
                ra.semlength = 1
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
            semesters[other.semester]['other'].append(other)
            
        return semesters
    
    def thesis_type(self):
        if 'thesis_type' in self.config:
            for code, description in THESIS_TYPE_CHOICES:
                if self.config['thesis_type'] == code:
                    return description
        return "Defence"

    def thesis_summary(self): 
        summary = ""
        if 'work_title' in self.config and self.config['work_title']:
            summary += self.config['work_title'] + " : "
        if 'thesis_location' in self.config and self.config['thesis_location']:
            summary += "(" + self.config['thesis_location'] + ") "
        if 'exam_date' in self.config and self.config['exam_date']:
            summary += self.config['exam_date'] + " "
        return summary

    def is_applicant(self):
        return self.current_status in STATUS_APPLICANT

    @classmethod
    def get_canonical(cls, person, semester=None):
        """ 
        Given a person, as of semester, try to find the student that looks 
        like the most correct record. 
       
        Returns a list of GradStudents, which may be empty if there are no 
        canonical records for this student in this semester..
        """
        
        if semester == None:
            semester = Semester.current() 

        student_records = GradStudent.objects.filter(person=person).order_by('-start_semester')

        students_and_statuses = [(gs, gs.status_as_of(semester)) for gs in student_records]

        # Always ignore None records. These students don't have a status for this semester.
        students_and_statuses = [(student, status) for student, status 
                in students_and_statuses if status != None]
        statuses = [status for student, status in students_and_statuses]

        # if we have (ACTIVE or APPLICANT) and DONE records, ignore DONE records.
        def intersect( l1, l2 ):
            return bool(set(l1) & set(l2))

        if intersect(STATUS_ACTIVE, statuses):
            return [student for (student, status) in students_and_statuses if status in STATUS_ACTIVE]
        elif intersect(STATUS_APPLICANT, statuses):
            return [student for (student, status) in students_and_statuses if status in STATUS_APPLICANT]
        elif 'LEAV' in statuses:
            return [student for (student, status) in students_and_statuses if status == 'LEAV']
        else:
            return [student for (student, status) in students_and_statuses]


    @classmethod
    def create( cls, person, program ):
        emplid = person.emplid 
        mother_tongue = coredata.queries.get_mother_tongue( emplid )
        passport_issued_by = coredata.queries.get_passport_issued_by( emplid )
        passport_issued_by = passport_issued_by[0:25]

        if passport_issued_by == "Canada":
            is_canadian = True
        elif coredata.queries.holds_resident_visa( emplid ):
            is_canadian = True
        else:
            is_canadian = False

        return GradStudent(person=person, 
            program=program,
            mother_tongue=mother_tongue, 
            passport_issued_by=passport_issued_by,
            is_canadian=is_canadian)
        
class GradProgramHistory(models.Model, ConditionalSaveMixin):
    student = models.ForeignKey(GradStudent, null=False, blank=False)
    program = models.ForeignKey(GradProgram, null=False, blank=False)
    start_semester = models.ForeignKey(Semester, null=False, blank=False,
            help_text="Semester when the student entered the program")
    starting = models.DateField(default=datetime.date.today)
    config = JSONField(default=dict) # addition configuration
        # 'sims_source': key indicating the SIMS record that imported to this, so we don't duplicate
    
    class Meta:
        ordering = ('-starting',)
    
    def __unicode__(self):
        return "%s: %s/%s" % (self.student.person, self.program, self.start_semester.name)



# documentation for the fields returned by GradStudent.letter_info
LETTER_TAGS = {
               'todays_date': 'today\'s date', 
               'title': '"Mr", "Miss", etc.',
               'first_name': 'student\'s first name',
               'last_name': 'student\'s last name',
               'emplid': 'student\'s emplid',
               'his_her' : '"his" or "her" (or use His_Her for capitalized)',
               'he_she' : '"he" or "she" (or use He_She for capitalized)',
               'him_her' : '"him" or "her" (or use Him_Her for capitalized)',
               'program': 'the program the student is enrolled in',
               'start_semester': 'student\'s first semester (e.g. "Summer 2000")',
               'start_year': 'year of student\'s first semester (e.g. "2000")',
               'promise': 'the amount of the [most recent] funding promise to the student (e.g. "$17,000")',
               'supervisor_name': "the name of the student's potential supervisor",
               'supervisor_hisher': 'pronoun for the potential supervisor ("his" or "her")',
               'supervisor_heshe': 'pronoun for the potential supervisor ("he" or "she")',
               'supervisor_himher': 'pronoun for the potential supervisor ("him" or "her")',
               'supervisor_email': 'potential supervisor\'s email address',
               'committee': 'display this student\'s entire committee',
               'sr_supervisor_name': 'the name of the student\'s senior supervisor',
               'sr_supervisor_hisher': 'pronoun for the senior supervisor ("his" or "her")',
               'sr_supervisor_heshe': 'pronoun for the senior supervisor ("he" or "she")',
               'sr_supervisor_himher': 'pronoun for the senior supervisor ("him" or "her")',
               'sr_supervisor_email': 'potential supervisor\'s email address',
               'defence_chair_name': 'the name of the student\'s defence chair', 
               'defence_chair_email': 'the email address of the student\'s defence chair',
               'sfu_examiner_name': 'the name of the student\'s internal (SFU) examiner', 
               'sfu_examiner_email': 'the email of the student\'s internal (SFU) examiner',
               'external_examiner_name': 'the name of the student\'s external examiner', 
               'external_examiner_email': 'the email of the student\'s external examiner',
               'co_sr_supervisor_name': 'the name of the student\'s co-senior supervisor', 
               'co_sr_supervisor_email': 'the email of the student\'s co-senior supervisor',
               'committee_1_name': 'the name of the student\'s first (non-senior) supervisor',
               'committee_1_email': 'the email of the student\'s first (non-senior) supervisor',
               'committee_2_name': 'the name of the student\'s second (non-senior) supervisor',
               'committee_2_email': 'the email of the student\'s second (non-senior) supervisor',
               'committee_3_name': 'the name of the student\'s third (non-senior) supervisor',
               'committee_3_email': 'the email of the student\'s third (non-senior) supervisor',
               'recent_empl': 'most recent employment ("teaching assistant" or "research assistant")',
               'tafunding': 'List of funding as a TA',
               'last_ta_start_date': 'the first day of the most recent TA contract granted to this student', 
               'last_ta_end_date': 'the last day of the most recent TA contract granted to this student', 
               'last_ta_total_salary': 'the total salary of the most recent TA contract granted to this student (Pay per BU * Total BU)', 
               'rafunding': 'List of funding as an RA',
               'last_ra_start_date': 'the first day of the most recent RA granted to this student', 
               'last_ra_end_date': 'the last day of the most recent RA granted to this student', 
               'last_ra_total_salary': 'the lump sum amount paid for the most recent RA granted to this student', 
               'last_ra_biweekly_salary': 'the biweekly pay for the most recent RA granted to this student',
               'scholarships': 'List of scholarships received',
               'sin': 'Student\'s SIN number, if available',
               'thesis_title': 'The title of the student\'s thesis, project, or extended essay',
               'thesis_date': 'The date of the student\'s thesis, project, or extended essay',
               'thesis_location': 'The location of the student\'s thesis, project, or extended essay',
               'research_area': 'The student\'s area of research',
               'qualifying_exam_date': 'The date of the student\'s qualifying exam',
               'qualifying_exam_location': 'The location of the student\'s qualifying exam'
               }

SUPERVISOR_TYPE_CHOICES = [
    ('SEN', 'Senior Supervisor'),
    ('COS', 'Co-senior Supervisor'),
    ('COM', 'Supervisor'),
    ('CHA', 'Defence Chair'),
    ('EXT', 'External Examiner'),
    ('SFU', 'SFU Examiner'),
    ('POT', 'Potential Supervisor'),
    ]
SUPERVISOR_TYPE = dict(SUPERVISOR_TYPE_CHOICES)
SUPERVISOR_TYPE_ORDER = {
    'SEN': 1,
    'COS': 2,
    'COM': 4,
    'CHA': 5,
    'EXT': 6,
    'SFU': 7,
    'POTTrue': 8, # potential with committee
    'POTFalse': 3, # potential without committee
    }

class Supervisor(models.Model, ConditionalSaveMixin):
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
    
    created_at = models.DateTimeField(default=datetime.datetime.now) # actually being used as an "effective as of"
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Committee member added by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Committee member modified by.', verbose_name='Last Modified By')
    config = JSONField(default=dict) # addition configuration
        # 'email': Email address (for external)
        # 'contact': Address etc (for external)
        # 'attend': 'P'/'A'/'T' for attending in person/in abstentia/by teleconference (probably only for external)
        # 'sims_source': key indicating the SIMS record that imported to this, so we don't duplicate
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

    def shortname(self):
        if self.supervisor:
            return self.supervisor.last_name
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
        self.student.clear_has_committee()
    
    def type_order(self):
        "Return key for sorting by supervisor_type"
        key = self.supervisor_type
        if key == 'POT':
            key += str(self.student.has_committee())
        return SUPERVISOR_TYPE_ORDER[key]
    
    def can_view_details(self):
        """
        Can this supervisor see the details of the student (funding, etc)? Yes for senior; yes for potential if no senior; no otherwise.
        """
        if self.supervisor_type == 'SEN':
            return True
        elif self.supervisor_type == 'POT':
            return not self.student.has_committee()
        else:
            return False


class GradRequirement(models.Model):
    """
    A requirement that a unit has for grad students
    """
    program = models.ForeignKey(GradProgram, null=False, blank=False)
    description = models.CharField(max_length=100)
    series = models.PositiveIntegerField(null=False, db_index=True, help_text='The category of requirement for searching by requirement, across programs')
    # .series is used to allow searching by type/series/category of requirement (e.g. "Completed Courses"),
    # instead of requiring selection of a specific GradRequirement in the search (which is too specific to a
    # program).
    # Values of .series are automatically maintained in self.save
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    hidden = models.BooleanField(default=False)

    def __unicode__(self):
        return u"%s" % (self.description)
    class Meta:
        unique_together = (('program', 'description'),)

    def save(self, *args, **kwargs):
        # maintain self.series as identifying the category of requirements across programs in this unit    
        with django.db.transaction.atomic():
            if not self.series:
                others = GradRequirement.objects \
                        .filter(description=self.description,
                                program__unit=self.program.unit)
                if others:
                    # use the series from an identically-named requirement
                    ser = others[0].series
                else:
                    # need a new series id
                    used = set(r.series for r in GradRequirement.objects.all())
                    try:
                        ser = max(used) + 1
                    except ValueError:
                        ser = 1
                
                self.series = ser
            
            super(GradRequirement, self).save(*args, **kwargs)
        

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
        'TRIN': 4,
        'CANC': 5,
        'ARIV': 5,
        'DEFR': 5,
        'ACTI': 6,
        'PART': 6,
        'LEAV': 7,
        'NOND': 7,
        'GAPL': 7,
        'GAPR': 7,
        'TROU': 8,
        'WIDR': 8,
        'GRAD': 8,
        'GONE': 8,
        'ARSP': 8,
        'DELE': 9,
        None: 9,
        }
class GradStatus(models.Model, ConditionalSaveMixin):
    """
    A "status" for a grad student: what were they doing in this range of semesters?
    """
    student = models.ForeignKey(GradStudent)
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, blank=False)
    start = models.ForeignKey(Semester, null=False, related_name="start_semester", verbose_name="Effective Semester",
            help_text="Semester when this status is effective")
    start_date = models.DateField(null=True, blank=True, verbose_name="Effective Date",
            help_text="Date this status is effective (optional)")
    end = models.ForeignKey(Semester, null=True, blank=True, related_name="end_semester",
            help_text="Final semester of this status: blank for ongoing")
    notes = models.TextField(blank=True, help_text="Other notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Set this flag if the status is no longer to be accessible.
    hidden = models.BooleanField(null=False, db_index=True, default=False)
    config = JSONField(default=dict) # addition configuration
        # 'sims_source': key indicating the SIMS record that imported to this, so we don't duplicate
        # 'in_from': for status=='TRIN', a Unit.slug where the student came from
        # 'out_to': for status=='TROU', a Unit.slug where the student went

    # If this is set to true, this status is not used in the calculation of the "status as of" logic.
    ignore_status = config_property('ignore_status', False)

    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted, set the hidden flag instead."

    def save(self, close_others=True, *args, **kwargs):
        if not self.start_date and self.status in STATUS_APPLICANT:
            self.start_date = datetime.datetime.now()

        super(GradStatus, self).save(*args, **kwargs)

        if close_others:
            # make sure any other statuses are closed
            other_gs = GradStatus.objects.filter(student=self.student, hidden=False, end__isnull=True).exclude(id=self.id)
            for gs in other_gs:
                gs.end = max(self.start, gs.start)
                gs.save(close_others=False)  

            # update gradstudent status fields
            self.student.update_status_fields()

    
    def __unicode__(self):
        return u"Grad Status: %s %s in %s" % (self.student, self.status, self.start.name)
    
    def get_short_status_display(self):
        return SHORT_STATUSES[self.status]

    @classmethod
    def overrun(cls, student, statuses_to_save):
        """
        For this GradStudent object, write new statuses over the existing set of statuses. 
        """
        existing_statuses = GradStatus.objects.filter(student=student)
        statuses_to_save_tuple = [(s.status, str(s.start.name)) for s in statuses_to_save]
        statuses_to_remove = []
        for existing_status in existing_statuses:
            if (existing_status.status, str(existing_status.start.name)) not in statuses_to_save_tuple:
                existing_status.hidden = True
                existing_status.save()
        for status in statuses_to_save:
            status.save()
        student.update_status_fields()

"""
Letters
"""

class LetterTemplate(models.Model):
    unit = models.ForeignKey(Unit, null=False, blank=False)
    label = models.CharField(max_length=150, null=False)
        # likely choices: visa, international, msc offer, phd offer, special student offer, qualifying student offer
    content = models.TextField(help_text="I.e. 'This is to confirm {{title}} {{last_name}} ... '")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Letter template created by.')
    hidden = models.BooleanField(default=False)
    config = JSONField(default=dict)  # Additional configuration for the template
        # 'body_font_size': the default font size for the letter.

    defaults = {'body_font_size': 12}
    body_font_size, set_body_font_size = getter_setter('body_font_size')

    def autoslug(self):
        return make_slug(self.unit.label + "-" + self.label)  
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
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
    closing = models.CharField(max_length=100, default="Sincerely")
    from_person = models.ForeignKey(Person, null=True)
    from_lines = models.TextField(help_text='Name (and title) of the signer, e.g. "John Smith, Program Director"')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Letter generation requseted by.')
    removed = models.BooleanField(default=False)

    config = JSONField(default=dict) # addition configuration for within the letter
        # data returned by grad.letter_info() is stored here.
        # 'use_sig': use the from_person's signature if it exists? (Users set False when a real legal signature is required.)

    defaults = {'use_sig': True}
    use_sig, set_use_sig = getter_setter('use_sig')


    def autoslug(self):
        return make_slug(self.student.slug + "-" + self.template.label)     
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    def __unicode__(self):
        return u"%s letter for %s" % (self.template.label, self.student)
    def save(self, *args, **kwargs):
        # normalize text so it's easy to work with
        if not self.to_lines:
            self.to_lines = ''
        self.to_lines = normalize_newlines(self.to_lines.rstrip())
        self.from_lines = normalize_newlines(self.from_lines.rstrip())
        self.content = normalize_newlines(self.content.rstrip())
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
        unique_together = (("unit", "name"),)
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

    def difference(self):
        """
        How much are we short on this promise?
        """
        return self.received() - self.amount


COMMENT_TYPE_CHOICES = [
        ('SCO', 'Scholarship'),
        ('TA', 'TA'),
        ('RA', 'RA'),
        ('OTH', 'Other'),
        ]
class FinancialComment(models.Model):
    student = models.ForeignKey(GradStudent)
    semester = models.ForeignKey(Semester, related_name="+")
    comment_type = models.CharField(max_length=3, choices=COMMENT_TYPE_CHOICES, default='OTH', blank=False, null=False)
    comment = models.TextField(blank=False, null=False)
    created_by = models.CharField(max_length=32, null=False, help_text='Entered by (userid)')
    created_at = models.DateTimeField(default=datetime.datetime.now)
    removed = models.BooleanField(default=False)
    
    def __unicode__(self):
        return "Comment for %s by %s" % (self.student.person.emplid, self.created_by)

class GradFlag(models.Model):
    unit = models.ForeignKey(Unit)
    label = models.CharField(max_length=100, blank=False, null=False)
    
    def __unicode__(self):
        return self.label
    class Meta:
        unique_together = (('unit', 'label'),)

class GradFlagValue(models.Model):
    student = models.ForeignKey(GradStudent)
    flag = models.ForeignKey(GradFlag)
    value = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s: %s" % (self.flag.label, self.value)

class SavedSearch(models.Model):
    person = models.ForeignKey(Person, null=True)
    query = models.TextField()
    config = JSONField(null=False, blank=False, default=dict)
    
    class Meta:
        #unique_together = (('person', 'query'),)
        pass
        
    defaults = {'name': ''}
    name, set_name = getter_setter('name')


class ProgressReport(models.Model):
    student = models.ForeignKey(GradStudent)
    result = models.CharField(max_length=5, 
                              choices=PROGRESS_REPORT_CHOICES, 
                              db_index=True)
    removed = models.BooleanField(default=False)
    date = models.DateField(default=datetime.date.today)
    config = JSONField(null=False, blank=False, default=dict)
    comments = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return u"(%s) %s Progress Report" % (str(self.date), 
                                             self.get_result_display())


def attachment_upload_to(instance, filename):
    return upload_path('gradnotes', str(datetime.date.today().year), filename)


class ExternalDocument(models.Model):
    student = models.ForeignKey(GradStudent)
    name = models.CharField(max_length=100, null=False,
                            help_text="A short description of what this file contains.")
    file_attachment = models.FileField(storage=UploadedFileStorage,
                                       upload_to=attachment_upload_to,
                                       max_length=500)
    file_mediatype = models.CharField(max_length=200, 
                                      editable=False)
    removed = models.BooleanField(default=False)
    date = models.DateField(default=datetime.date.today)
    config = JSONField(null=False, blank=False, default=dict)
    comments = models.TextField(blank=True, null=True)
    
    def __unicode__(self):
        return u"(%s) %s" % (str(self.date), self.name)
    
    def attachment_filename(self):
        """
        Return the filename only (no path) for the attachment.
        """
        _, filename = os.path.split(self.file_attachment.name)
        print "FILENAME:", filename
        return filename

