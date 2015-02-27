from coredata.queries import add_person, SIMSConn, SIMS_problem_handler, cache_by_args
from coredata.models import Semester
import datetime
from pprint import pprint

# in ps_acad_prog dates within about this long of the semester start are actually things that happen next semester
DATE_OFFSET = datetime.timedelta(days=28)

@SIMS_problem_handler
@cache_by_args
def grad_program_changes(acad_prog):
    db = SIMSConn()
    db.execute("""
        SELECT emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action, prog_reason,
            effdt, admit_term
        FROM ps_acad_prog
        WHERE acad_career='GRAD' AND acad_prog=%s
        ORDER BY effdt, effseq
    """, (acad_prog,))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_semesters(emplid):
    db = SIMSConn()
    db.execute("""
        SELECT emplid, strm, stdnt_car_nbr, withdraw_code, acad_prog_primary, unt_taken_prgrss
        FROM ps_stdnt_car_term
        WHERE acad_career='GRAD' AND emplid=%s
        ORDER BY strm
    """, (emplid,))
    return list(db)


class GradHappening(object):
    """
    Superclass to represent things that happen to grad students.
    """

class ProgramStatusChange(GradHappening):
    def __init__(self, emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action,
            prog_reason, effdt, admit_term):
        # argument order must match grad_program_changes query
        self.emplid = emplid
        self.stdnt_car_nbr = stdnt_car_nbr
        self.adm_appl_nbr = adm_appl_nbr
        self.acad_prog = acad_prog
        self.effdt = effdt
        self.admit_term = admit_term

        self.status = ProgramStatusChange.prog_status_translate(prog_status, prog_action, prog_reason)

    def __repr__(self):
        return "%s@%s is %s" % (self.emplid, self.stdnt_car_nbr, self.status)

    @staticmethod
    def prog_status_translate(prog_status, prog_action, prog_reason=None):
        """
        Convert a SIMS admission applicant status (e.g. "AD", "ADMT")
        into a Coursys Status Code (e.g. "OFFO")

        See ps_adm_action_tbl and ps_prog_rsn_tbl in reporting DB for some explanations of the codes.
        """
        st_ac = (prog_status, prog_action)

        # application-related
        if st_ac == ('AP', 'APPL'):
            return 'INCO'
        if st_ac == ('AP', 'RAPP'):
            # application for readmission
            return 'INCO'
        elif st_ac == ('CN', 'WAPP'):
            return 'DECL'
        elif st_ac == ('CN', 'WADM'):
            return 'INCO'
        elif st_ac == ('AD', 'ADMT'):
            return 'OFFO'
        elif st_ac == ('AD', 'COND'):
            # conditional offer
            return 'OFFO'
        elif st_ac == ('AC', 'MATR'):
            return 'CONF'
        elif st_ac == ('CN', 'DENY'):
            return 'REJE'
        elif st_ac == ('CN', 'ADRV'):
            return 'CANC'
        elif prog_action == 'RECN':
            # "reconsideration"
            return None
        elif prog_action == 'DEFR':
            # deferred start: probably implies start semester change
            return None

        elif prog_action == 'DATA':
            if prog_reason == 'APPR':
                # approved by department: close enough
                return 'OFFO'
            # updated data, like a program or start semester change
            return None
        elif prog_action in ['PRGC', 'PLNC']:
            # changed to different program/plan
            return None

        elif st_ac == ('AC', 'ACTV'):
            return 'ACTI'
        elif st_ac == ('DC', 'DISC'):
            return 'WIDR'
        elif st_ac == ('LA', 'LEAV'):
            return 'LEAV'
        elif st_ac == ('AC', 'RLOA'):
            return 'ACTI'
        elif st_ac == ('AC', 'RADM'):
            return 'ACTI'
        elif st_ac == ('CM', 'COMP'):
            return 'GRAD'

        raise ValueError, str((prog_status, prog_action, prog_reason))

class GradSemester(GradHappening):
    """
    Used to make sure we catch them being active: program status doesn't always record it.
    """
    def __init__(self, emplid, strm, stdnt_car_nbr, withdraw_code, acad_prog_primary, unt_taken_prgrss):
        # argument order must match grad_semesters query
        self.emplid = emplid
        self.strm = strm
        self.stdnt_car_nbr = stdnt_car_nbr
        self.withdraw_code = withdraw_code
        self.acad_prog_primary = acad_prog_primary
        self.unt_taken_prgrss = unt_taken_prgrss

    def __repr__(self):
        return "%s@%s %s in %s" % (self.emplid, self.stdnt_car_nbr, self.withdraw_code, self.strm)


def add_semester_happenings(emplid, timeline):
    print "--------------", emplid
    print timeline
    for gs in grad_semesters(emplid):
        h = GradSemester(*gs)
        print h


'''

def NEW_create_or_update_student(emplid, dry_run=False, verbosity=1)

    #print "---------------------------"
    print emplid
    p = add_person(emplid)
    prog_map = program_map()
    #pprint(coredata.queries.get_timeline(emplid))
    #pprint(grad_program_changes(emplid))
    #pprint(grad_semesters(emplid))

    happenings = []
    prog_changes = grad_program_changes(emplid)
    for car_nbr, acad_prog, action, reason, dt, admit_term, completion_term, adm_appl_nbr in prog_changes:
        dt = datetime.datetime.strptime(dt, '%Y-%m-%d').date()
        sem = Semester.get_semester(dt + DATE_OFFSET)
        prog = prog_map.get(acad_prog, None)
        if not prog:
            print "don't know about acad_prog %s" % (acad_prog)
            continue

        gs_possible = GradStudent.objects.filter(person__emplid=emplid, start_semester__name=admit_term)
        gs_possible = list(gs_possible)

        if len(gs_possible) == 0:
            print "need to create", (emplid, admit_term, adm_appl_nbr)
        elif len(gs_possible) > 1:
            print "multiple options", (emplid, admit_term, adm_appl_nbr)
        else:
            gs = gs_possible[0]
            print "found", (emplid, admit_term, adm_appl_nbr), gs.config.get('adm_appl_nbr', None)

    return

    grad_sems = grad_semesters(emplid)
    for strm, withdr, acad_prog, taken in grad_sems:
        sem = Semester.objects.get(name=strm)
        prog = prog_map[acad_prog]
        print sem, withdr, acad_prog, taken

'''




def NEW_import_unit_grads(unit, dry_run=False, verbosity=1):
    prog_map = program_map()
    acad_progs = [acad_prog for acad_prog, program in prog_map.iteritems() if program.unit == unit]
    #acad_progs = ['CPMBD']

    timelines = {}
    for acad_prog in acad_progs:
        appls = grad_program_changes(acad_prog)
        for a in appls:
            emplid = a[0]
            timeline = timelines.get(emplid, [])
            status = ProgramStatusChange(*a)
            timeline.append(status)
            timelines[emplid] = timeline

    for emplid, timeline in timelines.iteritems():
        add_semester_happenings(emplid, timeline)

    #print add_semester_happenings('301013710', timelines['301013710'])

    return
    '''
    gps = GradStudent.objects.filter(program__unit=unit, start_semester__name__gte='1137').select_related('person')
    emplids = [gs.person.emplid for gs in gps]
    emplids = ['301067285']

    for emplid in emplids:
        NEW_create_or_update_student(emplid, dry_run=dry_run, verbosity=verbosity)
        '''







from django.db import IntegrityError
from django.conf import settings
import coredata
from coredata.models import Semester, Unit
from grad.models import GradStudent, GradStatus, GradProgramHistory, GradProgram, Supervisor
from collections import defaultdict

IGNORE_CMPT_STUDENTS = True
def create_or_update_student( emplid, dryrun=False, verbose=False ):
    """
        Given an emplid, create (or update) a GradStudent record.
        If dryrun is true, do not call any .save() calls.
    """
    if verbose:
        print "Create/Update Student: ", emplid

    # First we generate a person to tie all of the generated records to.
    person = coredata.queries.find_or_generate_person( emplid )
    if verbose:
        print "\t", person

    prog_map = program_map()

    # This bit is really important: a combined query which makes a bunch of
    #  guesses as to what the student's actually been doing all this time.
    timeline = coredata.queries.get_timeline(emplid)
    if verbose:
        import json
        print "--- Timeline ---"
        print json.dumps( timeline, indent=2 )

    # Strip any programs from the timeline that aren't our grad programs
    timeline = [x for x in timeline if x['program_code'] in prog_map.keys()]
    # Split the programs into groups based on completion status
    #  groups are important, especially because we're bad about detecting
    #  program changes. If a student is in ESMSC one semester and ESPHD the
    #  next, without a withdrawal or completion between the two, we're going
    #  assume it is part of the same grad career.
    groups = split_timeline_into_groups(timeline)

    # keep track of which adm_appl_nbrs we've encountered
    #  if you're reading along from home, 'adm_appl_nbr' is a unique identifier
    #  for a single admission application. There should probably be about
    adm_appl_nbrs = []

    # For each group, and then each program in each group, try
    #  to reconcile this group with a GradStudent record that exists.
    for group_no, group in groups.iteritems():
        if verbose:
            print "\tGroup: ", group_no

        # ignore empty groups
        if len(group) < 1:
            continue

        first_program = group[0]
        last_program = group[-1]
        all_previous_programs = group[:-1]

        # if this program has an adm_appl_nbr, write down that we've seen it
        for program in group:
            if 'adm_appl_nbr' in program and program['adm_appl_nbr']:
                adm_appl_nbrs.append(str(program['adm_appl_nbr']))

        # this is a special case for CMPT.
        if IGNORE_CMPT_STUDENTS and first_program['program_code'].startswith("CP"):
            if verbose:
                print "\tIgnoring CMPT data"
            continue

        last_program_object = prog_map[last_program['program_code']]

        # does this person/program already exist?
        gradstudents = GradStudent.objects.filter(person=person, program=last_program_object)

        if len(gradstudents) < 1:
            if verbose:
                print "\tGrad student not found, creating"
            student = GradStudent.create( person, last_program_object )

            if not dryrun:
                if verbose:
                    print "saving GradStudent"
                student.save()
            else:
                if verbose:
                    print "dry run: not saving GradStudent."
        elif len(gradstudents) > 1:
            if verbose:
                print "\tRECOVERABLE ERROR: Somehow we found more than one GradStudent record for", last_program_object

            # try to use the adm_appl_nbr to reconcile things.
            if 'adm_appl_nbr' in first_program:
                with_adm_appl = [x for x in gradstudents if
                                    'adm_appl_nbr' in x.config
                                    and x.config['adm_appl_nbr'] == first_program['adm_appl_nbr'] ]
                if len(with_adm_appl) > 0:
                    student = with_adm_appl[0]
                    if verbose:
                        print "\t picking the one with adm_appl_nbr match: ", first_program['adm_appl_nbr']
                else:
                    student = gradstudents[0]
                    if verbose:
                        print "\t no matching adm_appl_nbr found, going with the first grad student record ", student
            else:
                student = gradstudents[0]
                if verbose:
                    print "\t no matching adm_appl_nbr found, going with ", student
        else:
            if verbose:
                print "\tGrad student found"
            student = gradstudents[0]

        # If we have an adm_appl_nbr, use it to build an admission history
        statuses_to_save = []
        if 'adm_appl_nbr' in first_program:
            student.config['adm_appl_nbr'] = first_program['adm_appl_nbr']
            if not dryrun:
                student.save()
        for program in group:
            if 'admission_records' in program:
                admission_records = program['admission_records']
                if verbose:
                    print "Admission Records:"
                    print admission_records
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
                if verbose:
                    print "\tFound Program History:", gph
            except GradProgramHistory.DoesNotExist:
                gph = GradProgramHistory(
                    student = student,
                    program = program_object,
                    start_semester = start_semester )
                if verbose:
                    print "\tCreating Program History:", gph
                if not dryrun:
                    if verbose:
                        print "saving GradProgramHistory."
                    gph.save()
                else:
                    if verbose:
                        print "dry run: not saving GradProgramHistory."

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
            if verbose:
                print "saving GradStatus objects"
            GradStatus.overrun(student, statuses_to_save)
        else:
            if verbose:
                print "dry run, not saving GradStatus"

        # We need the very startest of start dates and the very endest of end dates
        #  for this student to run the Supervisor query
        first_day_of_first_semester = Semester.objects.get( name=first_program['start'] ).start
        last_day_of_last_semester = Semester.objects.get( name=last_program['end'] ).end

        supervisory_committee = coredata.queries.get_supervisory_committee(
            emplid, first_day_of_first_semester, last_day_of_last_semester )

        supervisors_to_add = []
        for supervisor_sims, supervisor_emplid, supervisor_date in supervisory_committee:
            try:
                supervisor = coredata.queries.find_or_generate_person( supervisor_emplid )
            except IntegrityError as e:
                if verbose:
                    print e
                continue
            supervisor_type = supervisor_sims_to_supervisor_type( supervisor_sims )
            if not supervisor_type:
                continue
            s = find_or_create_supervisor( student, supervisor_type, supervisor, supervisor_date )
            supervisors_to_add.append(s)

        if not dryrun:
            for supervisor in supervisors_to_add:
                supervisor.save()

    # Create records for any spare adm_appl_nbrs
    all_adm_appl_nbrs = coredata.queries.get_adm_appl_nbrs(emplid)
    remaining_adm_appl_nbrs = [a for a in all_adm_appl_nbrs if str(a[0]) not in adm_appl_nbrs]
    if verbose:
        print "\t All Adm Appl Nbrs: ", all_adm_appl_nbrs
        print "\t Adm Appl Nbrs: ", adm_appl_nbrs
        print "\t Remaining Adm Appl Nbrs: ", remaining_adm_appl_nbrs

    for adm_appl_nbr, program_code in remaining_adm_appl_nbrs:
        if verbose:
            print "\tAdm Appl Nbr: ", adm_appl_nbr

        if IGNORE_CMPT_STUDENTS and program_code.startswith("CP"):
            if verbose:
                print "\tIgnoring CMPT data"
            continue

        if program_code not in prog_map.keys():
            if verbose:
                print "\t", program_code, " is not a grad program."
            continue

        program = prog_map[program_code]

        gradstudents = GradStudent.objects.filter(person=person, program=program)

        with_adm_appl = [s for s in gradstudents if 'adm_appl_nbr' in s.config and
                                                    s.config['adm_appl_nbr'] == adm_appl_nbr ]

        admission_records = coredata.queries.get_admission_records( emplid, adm_appl_nbr )
        if verbose:
            print "\tAdmission Records:"
            print "\t", admission_records

        if len(with_adm_appl) == 0:
            if verbose:
                print "\tNot found."
            student = GradStudent.create( person, program )
            student.config['adm_appl_nbr'] = adm_appl_nbr
            if not dryrun:
                student.save()
        else:
            student = with_adm_appl[0]
            if verbose:
                print "\t Found."

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
    if settings.DEPLOY_MODE != 'production':
        cmptunit = Unit.objects.get(label="CMPT")
        engunit = Unit.objects.get(label="ENSC")
        program_map = {
            'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
            'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPMCW': GradProgram.objects.get(label="MSc Project", unit=cmptunit),
            'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPGND': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPGQL': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
            'CPMBD': GradProgram.objects.get(label="MSc Big Data", unit=cmptunit),

            'ESMEN': GradProgram.objects.get(label="MEng", unit=engunit),
            'ESMAS': GradProgram.objects.get(label="MEng", unit=engunit),
            'ESPHD': GradProgram.objects.get(label="PhD", unit=engunit),
            'MSEPH': GradProgram.objects.get(label="PhD", unit=engunit),
            'MSEMS': GradProgram.objects.get(label="MEng", unit=engunit)
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
            'CPMBD': GradProgram.objects.get(label="MSc Big Data", unit=cmptunit),

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
    else:
        active_status = GradStatus(
            student = student,
            status = status,
            start = semester)
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
        return s[0]
    else:
        s = Supervisor(student=student,
                        supervisor=supervisor,
                        supervisor_type=supervisor_type,
                        updated_at=date)
        return s