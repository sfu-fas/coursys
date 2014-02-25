from django.db import models, transaction
from django.core.cache import cache
from coredata.models import Person, Unit, Semester, CAMPUS_CHOICES, Member
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from courselib.json_fields import getter_setter
from jsonfield import JSONField
from pages.models import _normalize_newlines
import re, itertools, datetime
import coredata.queries
from django.conf import settings
import json
from collections import defaultdict
many_newlines = re.compile(r'\n{3,}')

IGNORE_CMPT_STUDENTS = True
def create_or_update_student( emplid, dryrun=False ):
    """
        Given an emplid, create (or update) a GradStudent record.
        If dryrun is true, do not call any .save() calls. 
    """
    print "Create/Update Student: ", emplid

    person = coredata.queries.find_or_generate_person( emplid )
    #print "\t", person

    prog_map = program_map()
    timeline = coredata.queries.get_timeline(emplid)
    #print json.dumps( timeline, indent=2 )
    # strip any programs from the timeline that aren't our grad programs
    timeline = [x for x in timeline if x['program_code'] in prog_map.keys()]
    # split the programs into groups based on completion status
    groups = split_timeline_into_groups(timeline)

    adm_appl_nbrs = [] 
    for group_no, group in groups.iteritems(): 
        #print "\tGroup: ", group_no

        # ignore empty groups 
        if len(group) < 1:
            continue

        first_program = group[0]
        last_program = group[-1]
        all_previous_programs = group[:-1]

        if IGNORE_CMPT_STUDENTS and first_program['program_code'].startswith("CP"):
            #print "\tIgnoring CMPT data"
            continue

        for program in group:
            if 'adm_appl_nbr' in program and program['adm_appl_nbr']:
                adm_appl_nbrs.append(str(program['adm_appl_nbr']))

        last_program_object = prog_map[last_program['program_code']]
        
        # does this person/program already exist? 
        gradstudents = GradStudent.objects.filter(person=person, program=last_program_object)
       
        if len(gradstudents) < 1:
            print "\tGrad student not found, creating"
            student = GradStudent.create( person, last_program_object )
            if not dryrun:
                student.save()
            # create a new GradStudent
        elif len(gradstudents) > 1:
            #print "\tRECOVERABLE ERROR: Found more than one GradStudent record"
            if 'adm_appl_nbr' in first_program: 
                with_adm_appl = [x for x in gradstudents if 
                                    'adm_appl_nbr' in x.config 
                                    and x.config['adm_appl_nbr'] == first_program['adm_appl_nbr'] ]
                if len(with_adm_appl) > 0: 
                    student = with_adm_appl[0]
                    print "\t picking the one with adm_appl_nbr match: ", first_program['adm_appl_nbr']
                else:
                    student = gradstudents[0] 
                    print "\t no matching adm_appl_nbr found, going with ", student
            else:
                student = gradstudents[0]
                print "\t no matching adm_appl_nbr found, going with ", student
        else: 
            print "\tGrad student found"
            student = gradstudents[0]

        statuses_to_save = []
        if 'adm_appl_nbr' in first_program:
            student.config['adm_appl_nbr'] = first_program['adm_appl_nbr']
            if not dryrun:
                student.save()
        if 'admission_records' in first_program:
            admission_records = first_program['admission_records']
            admission_statuses = admission_records_to_grad_statuses( admission_records, student )
            for status in admission_statuses:
                statuses_to_save.append(status)

        # create a GradProgramHistory for every previous program
        for program in all_previous_programs: 
            program_object = prog_map[program['program_code']]
            start_semester = Semester.objects.get(name=program['start'])
            try:
                gph = GradProgramHistory.objects.get(
                    student = student, 
                    program = program_object,
                    start_semester = start_semester )
                #print "\tFound Program History:", gph
            except GradProgramHistory.DoesNotExist:
                gph = GradProgramHistory(
                    student = student, 
                    program = program_object,
                    start_semester = start_semester )
                #print "\tCreating Program History:", gph
                if not dryrun:
                    gph.save()

        # find/create a GradStatus "Active" at the first semester
        active_status = find_or_create_status( student, 'ACTI', Semester.objects.get(name=first_program['start']))
        statuses_to_save.append(active_status)

        on_leaves = coredata.queries.merge_leaves(group)
        
        # for every on-leave, create an LEAV status for the student
        # when that leave ends, create an ACTI status for the student 
        for leave_start_semester, leave_end_semester in on_leaves: 
            start_semester_object = Semester.objects.get(name=leave_start_semester)
            end_semester_object = Semester.objects.get(name=leave_end_semester)
            on_leave_status = find_or_create_status( student, 'LEAV', start_semester_object )
            statuses_to_save.append(on_leave_status)
            next_semester_object = end_semester_object.offset(1)
            if int(next_semester_object.name) < int(last_program['end']):
                active_again_status = find_or_create_status( student, 'ACTI', next_semester_object )
                statuses_to_save.append(active_again_status) 

        # how did this end? 
        if 'how_did_it_end' in last_program and last_program['how_did_it_end']:
            end_code = last_program['how_did_it_end']['code']
            end_semester = last_program['how_did_it_end']['semester']
            end_semester_object = Semester.objects.get(name=end_semester)
    
            if end_code == "COMP":
                # Graduated! 
                created_status = find_or_create_status( student, 'GRAD', end_semester_object )
            if end_code == "DISC":
                # Withdrawn!
                created_status = find_or_create_status( student, 'WIDR', end_semester_object )
            statuses_to_save.append(created_status)
        
        if not dryrun:
            GradStatus.overrun(student, statuses_to_save)

        first_day_of_first_semester = Semester.objects.get( name=first_program['start'] ).start
        last_day_of_last_semester = Semester.objects.get( name=last_program['end'] ).end

        supervisory_committee = coredata.queries.get_supervisory_committee( 
            emplid, first_day_of_first_semester, last_day_of_last_semester )

        supervisors_to_add = []
        for supervisor_sims, supervisor_emplid, supervisor_date in supervisory_committee:
            supervisor = coredata.queries.find_or_generate_person( supervisor_emplid )
            supervisor_type = supervisor_sims_to_supervisor_type( supervisor_sims )
            if not supervisor_type:
                continue
            s = find_or_create_supervisor( student, supervisor_type, supervisor, supervisor_date )
            supervisors_to_add.append(s)

        if not dryrun: 
            for supervisor in supervisors_to_add:
                supervisor.save()
    
    #create records for any spare adm_appl_nbrs
    all_adm_appl_nbrs = coredata.queries.get_adm_appl_nbrs(emplid)
    #print "\t All Adm Appl Nbrs: ", all_adm_appl_nbrs
    #print "\t Adm Appl Nbrs: ", adm_appl_nbrs
    remaining_adm_appl_nbrs = [a for a in all_adm_appl_nbrs if str(a[0]) not in adm_appl_nbrs]
    #print "\t Remaining Adm Appl Nbrs: ", remaining_adm_appl_nbrs

    for adm_appl_nbr, program_code in remaining_adm_appl_nbrs:
        #print "\tAdm Appl Nbr: ", adm_appl_nbr
        
        if IGNORE_CMPT_STUDENTS and program_code.startswith("CP"):
            #print "\tIgnoring CMPT data"
            continue

        if program_code not in prog_map.keys():
            #print "\t", program_code, " is not a grad program."
            continue

        program = prog_map[program_code] 
        
        gradstudents = GradStudent.objects.filter(person=person, program=program)

        with_adm_appl = [s for s in gradstudents if 'adm_appl_nbr' in s.config and 
                                                    s.config['adm_appl_nbr'] == adm_appl_nbr ]

        if len(with_adm_appl) == 0:
            #print "\tNot found."
            student = GradStudent.create( person, program )
            student.config['adm_appl_nbr'] = adm_appl_nbr
            if not dryrun:
                student.save()
        else:
            student = with_adm_appl[0]
            #print "\t Found."

        admission_records = coredata.queries.get_admission_records( emplid, adm_appl_nbr )
        admission_statuses = admission_records_to_grad_statuses( admission_records, student )
        
        if not dryrun:
            GradStatus.overrun(student, admission_statuses)

def split_timeline_into_groups( timeline ):
    """
        If we have a timeline containing
        CPMSC - 1094-1097 
        CPMZU - 1097-1127 - graduated,
        CPPHD - 1134-1147,
        then we want to separate this student into two groups
        {
            '0': [ {CPMSC...}, {CPMZU...} ], 
            '1': [ {CPPHD...} ]
        }
    """
    prog_groups = defaultdict(list)
    last_group = 0
    for program in timeline: 
        prog_groups[last_group].append( program )
        if 'how_did_it_end' in program and program['how_did_it_end']: 
            last_group = last_group + 1

    return prog_groups
            
def program_map():
    """
    Return a dict mapping SIMS's ACAD_PROG to GradProgram
    i.e.:
        { 'CPPHD': GradProgram.objects.get(label='PhD'... ) }
    """
    if settings.DEBUG:
        cmptunit = Unit.objects.get(label="CMPT")
        engunit = Unit.objects.get(label="ENG")
        program_map = {
            'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPMCW': GradProgram.objects.get(label="MSc Project", unit=cmptunit),
            'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPGND': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPGQL': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            
            'ESMEN': GradProgram.objects.get(label="M.Eng.", unit=engunit),
            'ESMAS': GradProgram.objects.get(label="M.A.Sc.", unit=engunit),
            'ESPHD': GradProgram.objects.get(label="Ph.D.", unit=engunit)
        }
    else:
        cmptunit = Unit.objects.get(label="CMPT")
        mechunit = Unit.objects.get(label="MSE")
        engunit = Unit.objects.get(label="ENSC")
        program_map = {
            'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPMCW': GradProgram.objects.get(label="MSc Course", unit=cmptunit),
            'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPGND': GradProgram.objects.get(label="Special", unit=cmptunit),
            'CPGQL': GradProgram.objects.get(label="Qualifying", unit=cmptunit),

            'ESMEN': GradProgram.objects.get(label="M.Eng.", unit=engunit),
            'ESMAS': GradProgram.objects.get(label="M.A.Sc.", unit=engunit),
            'ESPHD': GradProgram.objects.get(label="Ph.D.", unit=engunit),

            'MSEPH': GradProgram.objects.get(label="Ph.D.", unit=mechunit),
            'MSEMS': GradProgram.objects.get(label="M.A.Sc.", unit=mechunit),
        }
    return program_map

def get_admission_status_code( admission_action, admitted=False ):
    """ 
        Convert a SIMS admission applicant "action" code 
        (e.g. "ADMT")
        into a Coursys Status Code
        (e.g. "OFFO")
    """
    if admission_action in ["ADMT", "COND"]:
        return "OFFO"
    if admission_action == "APPL":
        return "COMP"
    if admission_action == "MATR":
        return "CONF"
    if admission_action == "DENY":
        return "REJE"
    if admission_action in ["WAPP", "WADM"]:
        if admitted: 
            return "DECL"
        else:
            return "EXPI"
    return None

def admission_records_to_grad_statuses( admission_records, student ):
    """
        Convert a list of admission records:
        [
            ('ADMIT', datetime.date('2012-10-10'), '1124'),
            ('MATR', datetime.date('2012-11-11'), '1124')
        ]
        into a list of GradStatus objects:
        [
            <GradStatus 'OFFO' 1124>,
            <GradStatus 'CONF' 1124>
        ]
    """
    return_list = []
    admitted = False
    for action, date, semester in admission_records:
        status_code = get_admission_status_code( action, admitted )
        if status_code == "OFFO": 
            admitted = True
        if status_code == None:
            continue
        semester_object = Semester.objects.get(name=semester)
        gs = find_or_create_status( student, status_code, semester_object )
        return_list.append(gs)
    return return_list 

def find_or_create_status( student, status, semester): 
    active_statuses = GradStatus.objects.filter(
        student = student,
        status = status, 
        start = semester)
    if len(active_statuses) > 0: 
        active_status = active_statuses[0]
        active_status.hidden = False
        #print "\tFound Status: ", status, active_status.start
    else:
        active_status = GradStatus(
            student = student,
            status = status, 
            start = semester)
        #print "\tCreated Status: ", status, active_status.start
    return active_status

def supervisor_sims_to_supervisor_type( supervisor_sims ):
    """
        supervisor_sims is 'Senior Supervisor', 'Supervisor', 'Internal Examiner', etc.

        convert these into one of our supervisor codes - e.g. "SEN" for Senior Supervisor
    """
    supervisor_sims = str(supervisor_sims)
    if supervisor_sims in [ "Chair", 
                            "Committee Chair",
                            "Chair of Nominating Committee",
                            "Co-Chair" ]:
        return 'CHA'
    if supervisor_sims == "Internal Examiner":
        return 'SFU'
    if supervisor_sims == "External Examiner":
        return 'EXT'
    if supervisor_sims in [ "Committee Member",
                            "Generic Committee Member",
                            "Member", 
                            "Member of Committee" ]:
        return 'COM'
    if supervisor_sims == "Senior Supervisor": 
        return 'SEN'
    if supervisor_sims == "Supervisor":
        return 'COS'
    if supervisor_sims == "Admission Staff Support":
        return None

def find_or_create_supervisor( student, supervisor_type, supervisor, date ):
    s = Supervisor.objects.filter(student=student, 
                                    supervisor=supervisor,
                                    supervisor_type=supervisor_type )
    if len(s) > 0:
        #print "\tFound Supervisor:", s[0]
        return s[0]
    else:
        s = Supervisor(student=student,
                        supervisor=supervisor, 
                        supervisor_type=supervisor_type, 
                        updated_at=date)
        #print "\tCreated Supervisor:", s
        return s

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
        ('APPL', 'Applicant'), # TODO: remove Applicant: not used in the real data
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
        )
STATUS_APPLICANT = ('APPL', 'INCO', 'COMP', 'INRE', 'HOLD', 'OFFO', 'REJE', 'DECL', 'EXPI', 'CONF', 'CANC', 'ARIV') # statuses that mean "applicant"
STATUS_CURRENTAPPLICANT = ('INCO', 'COMP', 'INRE', 'HOLD', 'OFFO', 'CONF', 'ARIV') # statuses that mean "currently applying"
STATUS_ACTIVE = ('ACTI', 'PART', 'NOND') # statuses that mean "still around"
STATUS_DONE = ('WIDR', 'GRAD', 'GONE', 'ARSP') # statuses that mean "done"
STATUS_INACTIVE = ('LEAV',) + STATUS_DONE # statuses that mean "not here"
STATUS_OBSOLETE = ('APPL', 'INCO', 'REFU', 'INRE', 'ARIV', 'GONE') # statuses we don't actually use anymore

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
    campus = models.CharField(max_length=5, choices=GRAD_CAMPUS_CHOICES, blank=True, db_index=True)

    english_fluency = models.CharField(max_length=50, blank=True, help_text="I.e. Read, Write, Speak, All.")
    mother_tongue = models.CharField(max_length=25, blank=True, help_text="I.e. English, Chinese, French")
    is_canadian = models.NullBooleanField()
    passport_issued_by = models.CharField(max_length=25, blank=True, help_text="I.e. US, China")
    comments = models.TextField(max_length=250, blank=True, help_text="Additional information.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    created_by = models.CharField(max_length=32, null=False, help_text='Grad Student created by.')
    modified_by = models.CharField(max_length=32, null=True, help_text='Grad Student modified by.', verbose_name='Last Modified By')
    
    # fields that are essentially denormalized caches for advanced search. Updated by self.update_status_fields()
    start_semester = models.ForeignKey(Semester, null=True, help_text="Semester when the student started the program.", related_name='grad_start_sem')
    end_semester = models.ForeignKey(Semester, null=True, help_text="Semester when the student finished/left the program.", related_name='grad_end_sem')
    current_status = models.CharField(max_length=4, null=True, choices=STATUS_CHOICES, help_text="Current student status", db_index=True)

    config = JSONField(default={}) # addition configuration
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
        'progress':''}

    #sin, set_sin = getter_setter('sin')
    applic_email, set_applic_email = getter_setter('applic_email')
    
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
        
        # make sure we have a GradProgramHistory object corresponding to current state
        #oldhist = GradProgramHistory.objects.filter(student=self, program=self.program)
        #if not oldhist:
        #    h = GradProgramHistory(student=self, program=self.program)
        #    h.save()

        super(GradStudent, self).save(*args, **kwargs)
    
    def status_as_of(self, semester=None):
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
        Update the self.start_semester, self.end_semester, self.current_status fields.
        """
        old = (self.start_semester_id, self.end_semester_id, self.current_status)
        self.start_semester = None
        self.end_semester = None
        self.current_status = None

        self.current_status = self.status_as_of()

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
            application_statuses = [status for status in all_gs if status.status=='COMP']

            if len(active_statuses) > 0:
                self.start_semester = active_statuses[0].start
            elif len(confirmed_statuses) > 0:
                self.start_semester = confirmed_statuses[-1].start
            elif len(offered_statuses) > 0:
                self.start_semester = offered_statuses[-1].start
            elif len(application_statuses) > 0:
                self.start_semester = application_statuses[-1].start

        # end_semester
        if 'end_semester' in self.config:
            if self.config['end_semester']:
                self.end_semester = Semester.objects.get(name=self.config['end_semester'])
            else:
                self.end_semester = None
        else:
            if self.current_status in STATUS_DONE:
                ends = [status for status in all_gs if status.status in STATUS_DONE]
                if len(ends) > 0:
                    end_status = ends[-1]
                    self.end_semester = end_status.start
            else:
                self.end_semester = None
        
        if old != (self.start_semester_id, self.end_semester_id, self.current_status):
            key = 'grad-activesem-%i' % (self.id)
            cache.delete(key)
            self.save()

    def _active_semesters(self):
        """
        Number of active and total semesters
        """
        # actually flips through every relevant semester and checks to see
        # their (final) status in that semester. The data is messy enough
        # that I don't see any better way.
        next_sem = Semester.current().offset(1)
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


    def active_semesters(self):
        """
        Number of active and total semesters (caches self._active_semesters).
        
        Invalidated by self.update_status_fields.
        """
        key = 'grad-activesem-%i' % (self.id)
        res = cache.get(key)
        if res:
            return res
        else:
            res = self._active_semesters()
            cache.set(key, res, 24*3600)
            return res


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
        """
        active, total = self.active_semesters()
        return u"%i/%i" % (active, total)
    
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
        startsem = self.start_semester
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
                supervisor_himher = "him"
            elif sgender == "F":
                supervisor_hisher = "her"
                supervisor_heshe = "she"
                supervisor_himher = "her"
            else:
                supervisor_hisher = "his/her"
                supervisor_heshe = "he/she"
                supervisor_himher = "him/her"
        else:
            supervisor_name = 'UNKNOWN'
            supervisor_email = 'UNKNOWN@sfu.ca'
            supervisor_hisher = 'his/her'
            supervisor_heshe = "he/she"
            supervisor_himher = "him/her"
        
        ls = { # if changing, also update LETTER_TAGS below with docs!
               # For security reasons, all values must be strings (to avoid presenting dangerous methods in templates)
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
                'supervisor_himher': supervisor_himher,
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
            semesters[sem]['other'].append(other)
            
        return semesters
    
    def thesis_type(self):
        if 'thesis_type' in self.config:
            for code, description in THESIS_TYPE_CHOICES:
                if self.config['thesis_type'] == code:
                    return description
        return "Defence"

    def thesis_summary(self): 
        summary = ""
        if 'work_title' in self.config:
            summary += self.config['work_title'] + " : "
        if 'thesis_location' in self.config:
            summary += "(" + self.config['thesis_location'] + ") "
        if 'exam_date' in self.config:
            summary += self.config['exam_date'] + " "
        return summary

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

        student_records = GradStudent.objects.filter(person=person)

        students_and_statuses = [(gs, gs.status_as_of(semester)) for gs in student_records]

        # Always ignore None records. These students don't have a status for this semester.
        students_and_statuses = [(student, status) for student, status 
                in students_and_statuses if status != None]
        statuses = [status for student, status in students_and_statuses]

        # if we have (ACTIVE or APPLICANT) and DONE records, ignore DONE records.
        def intersect( l1, l2 ):
            return bool(set(l1) & set(l2))

        if (intersect( STATUS_ACTIVE, statuses ) or 
            intersect( STATUS_APPLICANT, statuses ) or 
            'LEAV' in statuses):
            students_and_statuses = [(student, status) for student, status in 
                                        students_and_statuses if 
                                        status not in STATUS_INACTIVE]

        return student_records

    @classmethod
    def create( cls, person, program ):
        emplid = person.emplid 
        mother_tongue = coredata.queries.get_mother_tongue( emplid )
        passport_issued_by = coredata.queries.get_passport_issued_by( emplid )

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
        
class GradProgramHistory(models.Model):
    student = models.ForeignKey(GradStudent, null=False, blank=False)
    program = models.ForeignKey(GradProgram, null=False, blank=False)
    start_semester = models.ForeignKey(Semester, null=False, default=Semester.current,
            help_text="Semester when the student entered the program")
    starting = models.DateField(default=datetime.date.today)
    
    class Meta:
        ordering = ('-starting',)
    
    def __unicode__(self):
        return "%s: %s/%s" % (self.student.person, self.program, self.start_semester.name)



# documentation for the fields returned by GradStudent.letter_info
LETTER_TAGS = {
               'title': '"Mr", "Miss", etc.',
               'first_name': 'student\'s first name',
               'last_name': 'student\'s last name',
               'his_her' : '"his" or "her" (or use His_Her for capitalized)',
               'he_she' : '"he" or "she" (or use He_She for capitalized)',
               'program': 'the program the student is enrolled in',
               'start_semester': 'student\'s first semester (e.g. "Summer 2000")',
               'start_year': 'year of student\'s first semester (e.g. "2000")',
               'promise': 'the amount of the [most recent] funding promise to the student (e.g. "$17,000")',
               'supervisor_name': "the name of the student's potential supervisor",
               'supervisor_hisher': 'pronoun for the potential supervisor ("his" or "her")',
               'supervisor_heshe': 'pronoun for the potential supervisor ("he" or "she")',
               'supervisor_himher': 'pronoun for the potential supervisor ("him" or "her")',
               'supervisor_email': "potential supervisor's email address",
               'recent_empl': 'most recent employment ("teaching assistant" or "research assistant")',
               'tafunding': 'List of funding as a TA',
               'rafunding': 'List of funding as an RA',
               'scholarships': 'List of scholarships received',
               }

SUPERVISOR_TYPE_CHOICES = [
    ('SEN', 'Senior Supervisor'),
    ('COS', 'Co-senior Supervisor'),
    ('COM', 'Committee Member'),
    ('CHA', 'Defence Chair'),
    ('EXT', 'External Examiner'),
    ('SFU', 'SFU Examiner'),
    ('POT', 'Potential Supervisor'),
    ]
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
        # 'contact': Address etc (for external)
        # 'attend': 'P'/'A'/'T' for attending in person/in abstentia/by teleconference (probably only for external)
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
    # instead of requiring selection of a specifi GradRequirement in the search (which is too specific to a
    # program).
    # Values of .series are automatically maintained in self.save
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated At')
    hidden = models.BooleanField(default=False)
    def __unicode__(self):
        return u"%s" % (self.description)
    class Meta:
        unique_together = (('program', 'description'),)

    @transaction.atomic
    def save(self, *args, **kwargs):
        # maintain self.series as identifying the category of requirements across programs in this unit    
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
        None: 9,
        }
class GradStatus(models.Model):
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
        return u"Grad Status: %s %s" % (self.status, self.student)
    
    def status_order(self):
        "For sorting by status"
        return STATUS_ORDER[self.status]

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
                #print "Removing Status:", existing_status, existing_status.start
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
    salutation = models.CharField(max_length=100, default="To whom it may concern", blank=True)
    closing = models.CharField(max_length=100, default="Sincerely")
    from_person = models.ForeignKey(Person, null=True)
    from_lines = models.TextField(help_text='Name (and title) of the signer, e.g. "John Smith, Program Director"')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, null=False, help_text='Letter generation requseted by.')
    config = JSONField(default={}) # addition configuration for within the letter
        # data returned by grad.letter_info() is stored here.
        # 'use_sig': use the from_person's signature if it exists? (Users set False when a real legal signature is required.)
    
    defaults = {'use_sig': True}
    use_sig, set_use_sig = getter_setter('use_sig')
        

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

    def short(self):
        """
        How much are we short on this promise?
        """
        return self.amount - self.received()


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
    config = JSONField(null=False, blank=False, default={})
    
    class Meta:
        #unique_together = (('person', 'query'),)
        pass
        
    defaults = {'name': ''}
    name, set_name = getter_setter('name')

