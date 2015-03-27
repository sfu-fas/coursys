from django.db import transaction
from django.conf import settings
from coredata.queries import add_person, SIMSConn, SIMS_problem_handler, cache_by_args, get_supervisory_committee
from coredata.models import Semester, Unit
from grad.models import GradProgram, GradStudent, Supervisor, GradStatus, GradProgramHistory
from grad.models import STATUS_APPLICANT, SHORT_STATUSES, SUPERVISOR_TYPE
import datetime
import itertools
from collections import defaultdict
import intervaltree

# TODO: some Supervisors were imported from cortez as external with "userid@sfu.ca". Ferret them out
# TODO: adjust LEAV statuses depending on the NWD/WRD status from ps_stdnt_car_term?
# TODO: GradStudent.create does things: use it
# TODO: CMPT distinction between thesis/project/course in SIMS?

# import grads from these units (but CMPT gets special treatment)
IMPORT_UNIT_SLUGS = ['cmpt', 'ensc', 'mse']
# subset of STATUS_CHOICES that CMPT wants imported
CMPT_IMPORT_STATUSES = []

# in ps_acad_prog dates within about this long of the semester start are actually things that happen next semester
DATE_OFFSET = datetime.timedelta(days=30)
# ...even longer for dates of things that are startup-biased (like returning from leave)
DATE_OFFSET_START = datetime.timedelta(days=90)
ONE_DAY = datetime.timedelta(days=1)

SIMS_SOURCE = 'sims_source' # key in object.config to record where things came from

def build_semester_lookup():
    """
    Build data structure to let us easily look up date -> strm.
    """
    all_semesters = Semester.objects.all()
    intervals = ((s.name, Semester.start_end_dates(s)) for s in all_semesters)
    intervals = (
        intervaltree.Interval(st, en+ONE_DAY, name)
        for (name, (st, en)) in intervals)
    return intervaltree.IntervalTree(intervals)

semester_lookup = build_semester_lookup()

IMPORT_START_DATE = datetime.date(1990, 1, 1)
IMPORT_START_SEMESTER = semester_lookup[IMPORT_START_DATE].pop().data

# if we find students starting before this semester, don't import
RELEVANT_PROGRAM_START = '1031'

# before this, we don't have Semester objects anyway, so throw up our hands (but could go earlier if there were semesters)
RELEVANT_DATA_START = datetime.date(1993, 9, 1)

STRM_MAP = dict((s.name, s) for s in Semester.objects.all())

COMMITTEE_MEMBER_MAP = { # SIMS committee_role -> our Supervisor.supervisor_type
    'SNRS': 'SEN',
    'COSP': 'COS',
    'SUPR': 'COM',
    'MMBR': 'COM',
    'INTX': 'SFU',
    'EXTM': 'EXT',
    'CHAI': 'CHA',
    # not explained by ps_commit_role_tbl but found in SIMS
    'STDN': 'COM', # existing data point was a committee member
    'FADV': 'SEN', # existing data point was a senior supervisor
}


@SIMS_problem_handler
@cache_by_args
def grad_program_changes(acad_prog):
    """
    Records from ps_acad_prog about students' progress in this program. Rows become ProgramStatusChange objects.
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'ProgramStatusChange', emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action, prog_reason,
            effdt, effseq, admit_term, exp_grad_term
        FROM ps_acad_prog
        WHERE acad_career='GRAD' AND acad_prog=%s AND effdt>=%s AND admit_term>=%s
        ORDER BY effdt, effseq
    """, (acad_prog, IMPORT_START_DATE, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_appl_program_changes(acad_prog):
    """
    ps_adm_appl_data records where the fee has actually been paid: we don't bother looking at them until then.
    Rows become ApplProgramChange objects.

    Many of these will duplicate ps_acad_prog: the ProgramStatusChange is smart enough to identify them.
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'ApplProgramChange', prog.emplid, prog.stdnt_car_nbr, prog.adm_appl_nbr, prog.acad_prog, prog.prog_status, prog.prog_action, prog.prog_reason,
            prog.effdt, prog.effseq, prog.admit_term, prog.exp_grad_term
        FROM ps_adm_appl_prog prog
            LEFT JOIN dbcsown.ps_adm_appl_data data
                ON prog.emplid=data.emplid AND prog.acad_career=data.acad_career AND prog.stdnt_car_nbr=data.stdnt_car_nbr AND prog.adm_appl_nbr=data.adm_appl_nbr
        WHERE prog.acad_career='GRAD' AND prog.acad_prog=%s AND prog.effdt>=%s AND prog.admit_term>=%s
            AND ( data.appl_fee_status in ('REC', 'WVD')
                OR data.adm_appl_ctr in ('GRAW') )
        ORDER BY prog.effdt, prog.effseq
    """, (acad_prog, IMPORT_START_DATE, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_semesters(emplids):
    """
    Semesters when the student was taking classes: use to mark them active (since sometimes ps_acad_prog doesn't).
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'GradSemester', emplid, strm, stdnt_car_nbr, withdraw_code, acad_prog_primary, unt_taken_prgrss
        FROM ps_stdnt_car_term
        WHERE acad_career='GRAD' AND emplid in %s AND strm>=%s
            AND unt_taken_prgrss>0
        ORDER BY strm
    """, (emplids, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def committee_members(emplids):
    """
    Grad committee members for this person.

    I suspect the JOIN is too broad: possibly should be maximizing effdt in ps_stdnt_advr_hist?
    """
    db = SIMSConn()
    db.execute("""
        SELECT 'CommitteeMembership', st.emplid, st.committee_id, st.acad_prog, com.effdt, com.committee_type, mem.emplid, mem.committee_role
        FROM
            ps_stdnt_advr_hist st
            JOIN ps_committee com
                ON (com.institution=st.institution AND com.committee_id=st.committee_id AND st.effdt<=com.effdt)
            JOIN ps_committee_membr mem
                ON (mem.institution=st.institution AND mem.committee_id=st.committee_id AND com.effdt=mem.effdt)
        WHERE
            st.emplid in %s
        ORDER BY com.effdt""",
        (emplids,))
    return list(db)




def build_program_map():
    """
    Return a dict mapping SIMS's ACAD_PROG to GradProgram
    i.e.:
        { 'CPPHD': GradProgram.objects.get(label='PhD'... ) }
    """
    cmptunit = Unit.objects.get(label="CMPT")
    program_map = {
        'CPPHD': GradProgram.objects.get(label="PhD", unit=cmptunit),
        'CPPZU': GradProgram.objects.get(label="PhD", unit=cmptunit),
        'CPMSC': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
        'CPMZU': GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
        'CPMBD': GradProgram.objects.get(label="MSc Big Data", unit=cmptunit),
        'CPGQL': GradProgram.objects.get(label="Qualifying", unit=cmptunit),
        'CPMCW': GradProgram.objects.get(label="MSc Course", unit=cmptunit),
        'CPGND': GradProgram.objects.get(label="Special", unit=cmptunit),
    }
    if True or settings.DEPLOY_MODE == 'production':
        engunit = Unit.objects.get(label="ENSC")
        mechunit = Unit.objects.get(label="MSE")
        program_map['MSEPH'] = GradProgram.objects.get(label="Ph.D.", unit=mechunit)
        program_map['MSEMS'] = GradProgram.objects.get(label="M.A.Sc.", unit=mechunit)
        program_map['ESMEN'] = GradProgram.objects.get(label="M.Eng.", unit=engunit)
        program_map['ESMAS'] = GradProgram.objects.get(label="M.A.Sc.", unit=engunit)
        program_map['ESPHD'] = GradProgram.objects.get(label="Ph.D.", unit=engunit)

    return program_map

def build_reverse_program_map():
    """
    Reverse of the program map, returning lists of acad_prog that *might* be the source of one of our programs.

    Needed because CMPT's flavours of masters aren't reflected in SIMS.
    """
    program_map = build_program_map()
    rev_program_map = defaultdict(list)
    for acad_prog, gradprog in program_map.items():
        rev_program_map[gradprog].append(acad_prog)

    cmptunit = Unit.objects.get(label="CMPT")
    rev_program_map[GradProgram.objects.get(label="MSc Thesis", unit=cmptunit)].append('CPMCW')
    rev_program_map[GradProgram.objects.get(label="MSc Course", unit=cmptunit)].append('CPMSC')
    rev_program_map[GradProgram.objects.get(label="MSc Proj", unit=cmptunit)].append('CPMSC')
    return rev_program_map

class GradHappening(object):
    """
    Superclass to represent things that happen to grad students.
    """
    program_map = None
    def effdt_to_strm(self):
        "Look up the semester that goes with this date"
        # within a few days of the end of the semester, things applicable next semester are being entered
        offset = DATE_OFFSET
        if hasattr(self, 'status') and self.status == 'ACTI':
            offset = DATE_OFFSET_START
        elif isinstance(self, CommitteeMembership):
            offset = datetime.timedelta(days=0)

        if hasattr(self, 'status') and self.status == 'GRAD' and self.exp_grad_term:
            # Graduation strm is explicitly in there
            strm = self.exp_grad_term
        elif hasattr(self, 'status') and self.status in STATUS_APPLICANT:
            # we like application-related things to be effective in their start semester, not the "current"
            strm = self.admit_term
        else:
            try:
                strm = semester_lookup[self.effdt + offset].pop().data
            except KeyError:
                # ignore things
                # from the long-long ago
                assert self.effdt < RELEVANT_DATA_START
                strm = None

        self.strm = strm

    def acad_prog_to_gradprogram(self):
        """
        Turn self.acad_prog into a GradProgram in self.grad_program if possible. Also set the unit that goes with it.
        """
        if GradHappening.program_map is None:
            GradHappening.program_map = build_program_map()

        try:
            self.grad_program = GradHappening.program_map[self.acad_prog]
            self.unit = self.grad_program.unit
        except KeyError:
            self.grad_program = None
            self.unit = None

    def import_key(self):
        """
        Return a key that will uniquely identify this record so we can find it again later.

        Must be JSON-serializable (and comparable for equality after serializing/deserializing)
        """
        raise NotImplementedError


class ProgramStatusChange(GradHappening):
    """
    Record a row from ps_acad_prog
    """
    def __init__(self, emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action,
            prog_reason, effdt, effseq, admit_term, exp_grad_term):
        # argument order must match grad_program_changes query
        self.emplid = emplid
        self.stdnt_car_nbr = None
        self.app_stdnt_car_nbr = stdnt_car_nbr
        self.adm_appl_nbr = adm_appl_nbr
        self.acad_prog = acad_prog
        self.effdt = datetime.datetime.strptime(effdt, '%Y-%m-%d').date()
        self.admit_term = admit_term
        self.exp_grad_term = exp_grad_term

        self.prog_status = prog_status
        self.prog_action = prog_action
        self.prog_reason = prog_reason

        self.status = self.prog_status_translate()
        self.acad_prog_to_gradprogram()
        self.effdt_to_strm()

        # had to change sims_source status for these so ps_acad_prog and ps_adm_appl_prog results would identify
        self.oldkey = ['ps_acad_prog', emplid, 'GRAD', stdnt_car_nbr, effdt, effseq]
        self.key = ['ps_acad_prog', emplid, effdt, self.prog_status, self.prog_reason, self.acad_prog]

        self.in_career = False
        self.gradstatus = None

    def __repr__(self):
        return "%s at %s (%s)" % (self.status, self.effdt, self.strm)

    def prog_status_translate(self):
        """
        Convert a SIMS admission applicant status (e.g. "AD", "ADMT")
        into a Coursys Status Code (e.g. "OFFO")

        See ps_adm_action_tbl and ps_prog_rsn_tbl in reporting DB for some explanations of the codes.
        """
        st_ac = (self.prog_status, self.prog_action)

        # application-related
        if st_ac == ('AP', 'APPL'):
            return 'COMP'
        if st_ac == ('AP', 'RAPP'):
            # application for readmission
            return 'COMP'
        elif st_ac == ('CN', 'WAPP'):
            return 'DECL'
        elif st_ac == ('CN', 'WADM'):
            # cancelled application
            return None
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
        elif self.prog_action == 'RECN':
            # "reconsideration"
            return None
        elif self.prog_action == 'DEFR':
            # deferred start: probably implies start semester change
            return None

        elif self.prog_action == 'DATA':
            if self.prog_reason == 'APPR':
                # approved by department: close enough to ('AD', 'COND')
                return 'OFFO'
            # updated data, like a program or start semester change
            return None
        elif self.prog_action in ['PRGC', 'PLNC']:
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

        raise KeyError, str((self.prog_status, self.prog_action, self.prog_reason))

    def import_key(self):
        return self.key
    def appl_key(self):
        return [self.strm, self.prog_status, self.prog_reason, self.acad_prog]

    def status_config(self):
        "Additional entries for GradStatus.config when updating"
        return {}

    def find_existing_status(self, statuses, verbosity):
        # look for something previously imported from this record
        key = self.import_key()
        # ApplProgramChange can be the same as a ProgramStatusChange except different effdt: let the one sorted first
        # win, even if that means changing the sims_source (because ApplProgramChange has an earlier effdt, likely)
        if self.status in STATUS_APPLICANT:
            same_appl_key = [s for s in statuses
                    if 'appl_key' in s.config and s.config['appl_key'] == self.appl_key()]
            if same_appl_key:
                if len(same_appl_key) > 1:
                    raise ValueError, str(self.import_key())
                s = same_appl_key[0]
                s.config[SIMS_SOURCE] = key
                assert s.status == self.status
                return s

        # had to change sims_source status for these so ps_acad_prog and ps_adm_appl_prog results would identify
        # ... be sure to find the old ones too.
        existing = [s for s in statuses
                if SIMS_SOURCE in s.config and
                ((s.config[SIMS_SOURCE] == key)
                 or (s.config[SIMS_SOURCE] == self.oldkey and s.status==self.status))]
        if existing:
            s = existing[0]
            s.config[SIMS_SOURCE] = key
            assert s.status == self.status
            return s

        # look for a real match in old data
        similar = [s for s in statuses
                if s.start.name == self.strm
                and s.status == self.status
                and SIMS_SOURCE not in s.config]

        if similar:
            if len(similar) > 1:
                # multiple matches: try to match on effdt, or just pick one.
                datematch = [s for s in similar if s.start_date == self.effdt]
                if datematch:
                    return datematch[0]
            return similar[0]

    def find_similar_status(self, statuses, verbosity):
        # a hail-mary to find something manually entered that is
        # (1) close enough we think it's the same fact
        # (2) not found as "real" data to match something else in the first pass
        close_enough = [s for s in statuses
                if s.start.offset_name(-1) <= self.strm <= s.start.offset_name(1)
                and s.status == self.status
                and SIMS_SOURCE not in s.config
                and not hasattr(s, 'found_in_import')]
        if close_enough:
            if verbosity > 2:
                print "* Found similar (but imperfect) status for %s/%s is %s in %s" % (self.emplid, self.unit.slug, self.status, self.strm)
            return close_enough[0]


    def find_local_data(self, student_info, verbosity):
        if self.status:
            # do a first pass to find good matches
            statuses = student_info['statuses']
            st = self.find_existing_status(statuses, verbosity=verbosity)
            self.gradstatus = st

            if self.gradstatus:
                self.gradstatus.found_in_import = True
                assert st.status == self.status
                assert st.start == STRM_MAP[self.strm]


    def update_status(self, student_info, verbosity, dry_run):
        """
        Find/update GradStatus object for this happening
        """
        # grad status: don't manage for CMPT
        if self.unit.slug == 'cmpt' and self.status not in CMPT_IMPORT_STATUSES:
            return

        statuses = student_info['statuses']
        if self.gradstatus:
            st = self.gradstatus
        else:
            # try harder to find a local status we can use for this: anything close not found
            # by any find_local_data() call
            st = self.find_similar_status(statuses, verbosity=verbosity)
            if not st:
                # really not found: make a new one
                st = GradStatus(student=student_info['student'], status=self.status)
                statuses.append(st)
                if verbosity:
                    print "Adding grad status: %s/%s is '%s' as of %s." % (self.emplid, self.unit.slug, SHORT_STATUSES[self.status], self.strm)

        self.gradstatus = st
        self.gradstatus.found_in_import = True

        assert st.status == self.status
        st.start = STRM_MAP[self.strm]
        st.start_date = self.effdt
        st.config[SIMS_SOURCE] = self.import_key()
        st.config.update(self.status_config())
        if self.status in STATUS_APPLICANT:
            # stash this so we can identify ApplProgramChange and ProgramStatusChange with different effdt
            self.gradstatus.config['appl_key'] = self.appl_key()

        if not dry_run:
            st.save_if_dirty()

        # re-sort if we added something, so we find things right on the next check
        student_info['statuses'].sort(key=lambda ph: (ph.start.name, ph.start_date or datetime.date(1900,1,1)))


    def update_program_history(self, student_info, verbosity, dry_run):
        """
        Find/update GradProgramHistory object for this happening
        """
        if self.unit.slug == 'cmpt':
            return

        programs = student_info['programs']
        key = self.import_key()
        if self.strm < student_info['real_admit_term']:
            # program change could happen before admit: we take those as effective the student's admit term
            strm = student_info['real_admit_term']
        else:
            strm = self.strm

        previous_history = [p for p in programs if p.start_semester.name <= strm]
        need_ph = False
        if previous_history:
            # there is a previously-known program: make sure it matches
            ph = previous_history[-1]
            if ph.program != self.grad_program:
                # current program isn't what we found
                # ... but is there maybe two program changes in one semester?
                similar_history = [p for p in programs if p.start_semester == ph.start_semester
                        and p.program == self.grad_program]
                if similar_history:
                    ph = similar_history[0]
                else:
                    need_ph = True

        else:
            # maybe the next-known program change is to the same program? If so, move it back.
            next_history = [p for p in programs if p.start_semester.name > strm]
            if next_history and next_history[0].program == self.grad_program:
                if verbosity > 1:
                    print "* Adjusting program change start: %s/%s in %s as of %s." % (self.emplid, self.unit.slug, self.grad_program.slug, strm)
                ph = next_history[0]
                ph.start_semester = STRM_MAP[strm]
                ph.starting = self.effdt
            else:
                # no history: create
                need_ph = True

        # make sure we don't duplicate: have a last look for an old import
        existing_history = [p for p in programs if
                SIMS_SOURCE in p.config and (p.config[SIMS_SOURCE] == key or p.config[SIMS_SOURCE] == self.oldkey)]
        if existing_history:
            ph = existing_history[0]
            need_ph = False

        if need_ph:
            if (verbosity and previous_history) or verbosity > 1:
                # don't usually report first ever ProgramHistory because those are boring
                print "Adding program change: %s/%s in %s as of %s." % (self.emplid, self.unit.slug, self.grad_program.slug, strm)
            ph = GradProgramHistory(student=student_info['student'], program=self.grad_program,
                    start_semester=STRM_MAP[strm], starting=self.effdt)
            ph.config[SIMS_SOURCE] = key
            student_info['programs'].append(ph)
            student_info['programs'].sort(key=lambda p: (p.start_semester.name, p.starting))
        else:
            if SIMS_SOURCE not in ph.config or ph.config[SIMS_SOURCE] == self.oldkey:
                ph.config[SIMS_SOURCE] = key

        if not dry_run:
            ph.save_if_dirty()


    def update_local_data(self, student_info, verbosity, dry_run):
        if self.status:
            # could be just a program change, but no status
            self.update_status(student_info, verbosity, dry_run)
        if self.grad_program:
            # CareerUnitChangeOut/CareerUnitChangeIn subclasses don't have grad_program and don't change program
            self.update_program_history(student_info, verbosity, dry_run)


class ApplProgramChange(ProgramStatusChange):
    """
    Like ProgramStatusChange except holding records from ps_adm_appl_prog.
    """
    pass  # I like subclasses.


class GradSemester(GradHappening):
    """
    Records a semester the student was taking classes (from ps_stdnt_car_term).

    Used to make sure we catch them being active: ps_acad_prog doesn't always record it.
    """
    def __init__(self, emplid, strm, stdnt_car_nbr, withdraw_code, acad_prog_primary, unt_taken_prgrss):
        # argument order must match grad_semesters query
        self.emplid = emplid
        self.strm = strm
        self.stdnt_car_nbr = stdnt_car_nbr
        self.withdraw_code = withdraw_code
        self.acad_prog = acad_prog_primary
        self.unt_taken_prgrss = unt_taken_prgrss
        self.status = 'ACTI'

        self.semester = STRM_MAP[self.strm]
        self.effdt = self.semester.start # taking classes starts at the start of classes

        self.acad_prog_to_gradprogram()

        self.adm_appl_nbr = None
        self.in_career = False

    def __repr__(self):
        return "%s in %s" % (self.withdraw_code, self.strm)

    def import_key(self):
        return ['ps_stdnt_car_term', self.emplid, self.strm]

    def find_local_data(self, student_info, verbosity):
        pass

    def update_local_data(self, student_info, verbosity, dry_run):
        if self.grad_program.unit.slug == 'cmpt' and 'ACTI' not in CMPT_IMPORT_STATUSES:
            return

        # make sure the student is "active" as of the start of this semester, since they're taking courses
        statuses = student_info['statuses']
        semester = self.semester
        effdt = self.effdt
        key = self.import_key()

        # Option 1: we're already active
        effective_statuses = [s for s in statuses if s.start.name <= self.strm
                and (not s.start_date or s.start_date <= effdt)]
        if effective_statuses and effective_statuses[-1].status == 'ACTI':
            s = effective_statuses[-1]
            if SIMS_SOURCE not in s.config:
                s.config[SIMS_SOURCE] = key
                if not dry_run:
                    s.save()
            return

        # Option 2: there's an active status this semester, but it's not the most recent
        active_semester_statuses = [s for s in statuses if s.start.name == self.strm and s.status == 'ACTI']
        if active_semester_statuses:
            st = active_semester_statuses[-1]
            if SIMS_SOURCE in st.config and st.config[SIMS_SOURCE] == key:
                # This happens for a couple of students with a 'confirmed acceptance' on the same effdt as the semester start
                # Kick it to make it effective for this semester, but don't bother reporting it.
                effdt = effdt + datetime.timedelta(days=1)
            elif verbosity > 1:
                print "* Adjusting date of grad status: %s/%s is '%s' as of %s (was taking courses)." % (self.emplid, self.unit.slug, SHORT_STATUSES['ACTI'], self.strm)

            st.start_date = effdt
            st.config[SIMS_SOURCE] = key
            if not dry_run:
                st.save()
        else:
            # Option 3: need to add an active status
            if verbosity:
                print "Adding grad status: %s/%s is '%s' as of %s (was taking courses)." % (self.emplid, self.unit.slug, SHORT_STATUSES['ACTI'], self.strm)
            st = GradStatus(student=student_info['student'], status='ACTI', start=semester,
                    start_date=effdt)
            st.config[SIMS_SOURCE] = key
            if not dry_run:
                st.save()
            student_info['statuses'].append(st)

        # re-sort if we added something, so we find things right on the next check
        student_info['statuses'].sort(key=lambda ph: (ph.start.name, ph.start_date or datetime.date(1900,1,1)))



class CommitteeMembership(GradHappening):
    found_people = None
    def __init__(self, emplid, committee_id, acad_prog, effdt, committee_type, sup_emplid, committee_role):
        # argument order must match committee_members query
        self.emplid = emplid
        self.adm_appl_nbr = None
        self.stdnt_car_nbr = None
        self.committee_id = committee_id
        self.acad_prog = acad_prog
        self.effdt = datetime.datetime.strptime(effdt, '%Y-%m-%d').date()
        self.sup_emplid = sup_emplid
        self.committee_type = committee_type
        self.committee_role = committee_role

        self.acad_prog_to_gradprogram()
        self.effdt_to_strm()
        self.in_career = False

        # emplid -> Person map, to keep queries to a minimum
        if not CommitteeMembership.found_people:
            CommitteeMembership.found_people = dict((s.supervisor.emplid, s.supervisor)
                    for s in Supervisor.objects.all().select_related('supervisor')
                    if s.supervisor and s.supervisor.emplid)


        if self.sup_emplid == '301001497':
            # Our friend Bob Two Studentnumbers
            self.sup_emplid = '200011069'

    def __repr__(self):
        return "%s as %s for %s" % (self.sup_emplid, self.committee_role, self.acad_prog)

    def find_local_data(self, student_info, verbosity):
        pass

    def import_key(self):
        return [self.committee_id, self.effdt, self.committee_type, self.sup_emplid, self.committee_role]

    def update_local_data(self, student_info, verbosity, dry_run):
        if self.grad_program.unit.slug == 'cmpt':
            return

        key = self.import_key()
        local_committee = student_info['committee']
        sup_type = COMMITTEE_MEMBER_MAP[self.committee_role]

        # cache People objects, so we don't query for them too much.
        if self.sup_emplid in CommitteeMembership.found_people:
            p = CommitteeMembership.found_people[self.sup_emplid]
        else:
            p = add_person(self.sup_emplid, external_email=True, commit=(not dry_run))
            CommitteeMembership.found_people[self.sup_emplid] = p

        matches = [m for m in local_committee if m.supervisor == p and m.supervisor_type == sup_type]
        if matches:
            member = matches[0]
        else:
            similar = [m for m in local_committee if m.supervisor == p]
            if len(similar) > 0:
                if verbosity > 2:
                    print "* Found similar (but imperfect) committee member for %s is a %s for %s/%s" % (p.name(), SUPERVISOR_TYPE[sup_type], self.emplid, self.unit.slug)
                member = similar[0]
            else:
                if verbosity:
                    print "Adding committee member: %s is a %s for %s/%s" % (p.name(), SUPERVISOR_TYPE[sup_type], self.emplid, self.unit.slug)
                member = Supervisor(student=student_info['student'], supervisor=p, supervisor_type=sup_type)
                member.created_at = self.effdt
                local_committee.append(member)

        if SIMS_SOURCE not in member.config:
            # record (the first) place we found this fact
            member.config[SIMS_SOURCE] = key
            # if it wasn't the product of a previous import it was hand-entered: take the effdt from SIMS
            member.created_at = self.effdt

        # TODO: try to match up external members with new real ones? That sounds hard.
        # TODO: remove members if added by this import (in the past) and not found in the newest committee version

        if not dry_run:
            member.save_if_dirty()



class CareerUnitChangeOut(ProgramStatusChange):
    """
    Record a inter-unit transfer away from this program.
    """
    # inherits ProgramStatusChange so we can use the find_existing_status and find_similar_status functionality
    def __init__(self, emplid, adm_appl_nbr, unit, otherunit, effdt, admit_term):
        """
        Represents a transfer into or out of a unit within one grad career: since GradStudent is limited to one unit,
        we must split careers around unit transfers
        """
        self.emplid = emplid
        self.adm_appl_nbr = adm_appl_nbr
        self.effdt = effdt
        self.stdnt_car_nbr = None
        self.grad_program = None
        self.oldkey = None

        if self.inout() == 'out':
            self.status = 'TROU'
        else:
            self.status = 'TRIN'

        # CareerUnitChangeOut.unit is the old unit and otherunit is the new unit
        # for CareerUnitChangeIn they are reversed.
        self.unit = unit
        self.otherunit = otherunit

        self.effdt_to_strm()
        self.strm = max(admit_term, self.strm) # make sure transfer happens after any application-related statuses
        self.in_career = False

    def inout(self):
        return 'out'
    def import_key(self):
        return ['unit_change_'+self.inout(), self.emplid, self.adm_appl_nbr, str(self.effdt), self.unit.slug, self.otherunit.slug]

    def status_config(self):
        "Additional entries for GradStatus.config when updating"
        return {'out_to': self.otherunit.slug}


class CareerUnitChangeIn(CareerUnitChangeOut):
    """
    Record a inter-unit transfer into this program.
    """
    def inout(self):
        return 'in'

    def status_config(self):
        "Additional entries for GradStatus.config when updating"
        return {'in_from': self.otherunit.slug}


class GradTimeline(object):
    """
    A complete timeline of all grad-student-related things that happened to this person.

    ProgramStatusChange and ApplProgramChange are added as these objects are created (as part of deciding which people
    we're interested in).

    GradSemester and CommitteeMembership are added by methods here.

    CareerUnitChangeOut and CareerUnitChangeIn are added after splitting the happenings into careers, when we know
    that transferring between units is actually happening.
    """
    def __init__(self, emplid):
        self.emplid = emplid
        self.happenings = []
        self.careers = []

    def __repr__(self):
        return 'GradTimeline(%s, %s)' % (self.emplid, repr(self.happenings))

    def add(self, happening):
        self.happenings.append(happening)

    def sort_happenings(self):
        self.happenings.sort(key=lambda h: (h.strm, h.effdt))

    def split_careers(self, verbosity=1):
        """
        Take all of the happenings we found and split them into careers, with each representing one GradStudent object.

        Rules:
        careers have to be within one unit
        a career is usually started by applying for a program (or by transferring between units)
        """

        # handle committee memberships separately: if they select a committee after applying for a different program,
        # we need to notice.
        self.sort_happenings()
        happenings = [h for h in self.happenings if h.grad_program]

        # pass 1: we know the adm_appl_nbr
        for h in happenings:
            if h.adm_appl_nbr:
                cs = [c for c in self.careers if c.unit == h.unit and c.adm_appl_nbr == h.adm_appl_nbr]
                if len(cs) > 1:
                    raise ValueError, str(cs)
                elif len(cs) == 1:
                    c = cs[0]
                else:
                    c = GradCareer(self.emplid, h.adm_appl_nbr, h.app_stdnt_car_nbr, h.grad_program.unit)
                    self.careers.append(c)

                c.add(h)

        # pass 2: make sure all ProgramStatusChange objects are somewhere, even without adm_appl_nbrs
        for h in happenings:
            if h.in_career or not isinstance(h, ProgramStatusChange):
                continue

            # assumption: if no adm_appl_nbr then they didn't apply but it's the same unit, so it's the same GradCareer
            possible_careers = [c for c in self.careers if c.unit == h.unit]
            if len(possible_careers) == 1:
                c = possible_careers[0]
                c.add(h)
            elif len(possible_careers) > 1:
                # If multiple, use the (often odd) stdnt_car_nbr to choose
                # re-admits seem to have same stdnt_car_nbr, so use admit_term to guess
                possible_careers = [c for c in self.careers if c.unit == h.unit and c.app_stdnt_car_nbr == h.app_stdnt_car_nbr and c.admit_term <= h.strm]
                if len(possible_careers)>1 and h.prog_action in ['LEAV', 'RLOA', 'DISC', 'COMP', 'RADM']:
                    # had to be activated for these to happen, so use that to decide
                    possible_careers = [c for c in possible_careers if c.possibly_active_on(h.effdt)]

                if len(possible_careers) == 1:
                    c = possible_careers[0]
                    c.add(h)
                elif len(possible_careers) > 1:
                    if h.prog_action == 'DATA' and not h.status:
                        # these aren't really carrying info, so drop
                        h.in_career = True
                    else:
                        raise ValueError, "Multiple career options for happening %s for %s. %s" % (h, self.emplid, possible_careers)
                else:
                    #print h.prog_action in ['LEAV', 'RLOA', 'DISC', 'RADM'], (h.prog_action, h.status)

                    # make sure that "active program" filter didn't cause an inappropriate new career
                    assert h.prog_action not in ['LEAV', 'RLOA', 'DISC', 'COMP']

                    # it's a new career, conjured out of the ether

            if not h.in_career:
                # no existing program: must be new.
                c = GradCareer(self.emplid, h.adm_appl_nbr, h.app_stdnt_car_nbr, h.grad_program.unit)
                self.careers.append(c)
                c.add(h)

        # pass 3: what program are they actually in at that time?
        for h in happenings:
            if h.in_career:
                continue

            in_unit_careers = [c for c in self.careers if c.unit == h.unit]
            if len(in_unit_careers) == 1:
                # why kill ourselves if there's only one option?
                c = in_unit_careers[0]
                c.add(h)
                continue

            possible_careers = [c for c in self.careers if c.unit == h.unit and c.possibly_active_on(h.effdt) and c.program_as_of(h.effdt) == h.acad_prog]
            if possible_careers:
                # If active in the same program two or more times on this date, throw up hands and choose the last-begun.
                possible_careers.sort(key=lambda c: c.admit_term)
                c = possible_careers[-1]
                c.add(h)
            else:
                # Try harder to find somewhere to put this: were they in that program in the past?
                possible_careers = [c for c in self.careers if c.unit == h.unit and c.program_as_of(h.effdt) == h.acad_prog and c.admit_term <= h.strm]
                possible_careers.sort(key=lambda c: c.admit_term)
                if possible_careers:
                    c = possible_careers[-1]
                    c.add(h)
                else:
                    if isinstance(h, CommitteeMembership):
                        # Try even harder: some where given grad committees before they even started
                        possible_careers = [c for c in self.careers if c.unit == h.unit and c.last_program == h.acad_prog]
                        possible_careers.sort(key=lambda c: c.admit_term)
                        if possible_careers:
                            c = possible_careers[-1]
                            c.add(h)
                    elif isinstance(h, GradSemester):
                        # Try even harder: there is an occasional grad semester associated with a just-transferred-out program
                        possible_careers = [c for c in self.careers if c.unit == h.unit and c.program_as_of(h.effdt-datetime.timedelta(days=7)) == h.acad_prog and c.admit_term <= h.strm]
                        if possible_careers:
                            c = possible_careers[-1]
                            c.add(h)

                    # admit failure in a few cases
                    if not h.in_career and isinstance(h, CommitteeMembership):
                        # Committee member added to one program after student changed to another: drop this one.
                        # Committee membership for student's new program should be in another happening.
                        h.in_career = True
                    elif not h.in_career and isinstance(h, GradSemester) and h.effdt - datetime.timedelta(days=730) < IMPORT_START_DATE:
                        # student in classes just after the beginning of time: we missed the career
                        h.in_career = True



        dropped = [h for h in happenings if not h.in_career]
        if dropped:
            raise ValueError, 'Some happenings got dropped for %s! %s' % (self.emplid, dropped)

        for c in self.careers:
            c.sort_happenings()

        self.add_transfer_happenings()
        self.junk_application_only_careers()


    def add_transfer_happenings(self):
        """
        Categorize the careers by adm_appl_nbr and acad_prog.stdnt_car_nbr: being the same means same program
        application event. If those were split between departments, then it's an inter-departmental transfer.

        Those need transfer out/in happenings added.
        """
        adm_appl_groups = itertools.groupby(self.careers, lambda c: (c.adm_appl_nbr, c.app_stdnt_car_nbr))
        for (adm_appl_nbr, app_stdnt_car_nbr), careers in adm_appl_groups:
            careers = list(careers)
            if len(careers) == 1:
                continue

            # sort by order they happen: heuristically, effdt of first happening in career
            careers.sort(key=lambda c: c.happenings[0].effdt)

            # we have an inter-department transfer: create transfer in/out happenings
            for c_out, c_in in zip(careers, careers[1:]):
                effdt = c_in.happenings[0].effdt
                t_out = CareerUnitChangeOut(emplid=c_out.emplid, adm_appl_nbr=c_out.adm_appl_nbr, unit=c_out.unit,
                        otherunit=c_in.unit, effdt=effdt, admit_term=c_out.admit_term)
                t_in = CareerUnitChangeIn(emplid=c_in.emplid, adm_appl_nbr=c_in.adm_appl_nbr, unit=c_in.unit,
                        otherunit=c_out.unit, effdt=effdt, admit_term=c_in.admit_term)
                c_out.happenings.append(t_out)
                c_in.happenings.insert(0, t_in)


    def junk_application_only_careers(self):
        """
        There are a lot of careers with just one ApplProgramChange representing the application (with no followup
        decision). We don't really want those.
        """
        for c in self.careers:
            c.application_only = False
            if len(c.happenings) == 1:
                h = c.happenings[0]
                if isinstance(h, ApplProgramChange) and (h.prog_status, h.prog_action) == ('AP', 'APPL'):
                    c.application_only = True

        self.careers = [c for c in self.careers if not c.application_only]

    def find_rogue_local_data(self, verbosity, dry_run):
        """
        Look for things in the local data that don't seem to match reality.
        """
        if self.unit.slug == 'cmpt':
            # don't worry about these for now
            return

        existing_grads = set(GradStudent.objects
                .filter(program__unit=self.unit, person__emplid=self.emplid, start_semester__name__gt=RELEVANT_PROGRAM_START)
                .select_related('start_semester', 'program__unit'))
        found_grads = set(c.gradstudent for c in self.careers if c.gradstudent and c.gradstudent.id)
        extra_grads = existing_grads - found_grads
        if verbosity:
            for gs in extra_grads:
                if SIMS_SOURCE in gs.config:
                    # trust us-from-the-past
                    continue
                print 'Rogue grad student: %s in %s starting %s' % (self.emplid, gs.program.slug, gs.start_semester.name if gs.start_semester else '???')




class GradCareer(object):
    """
    One grad career as we understand it (a grad.models.GradStudent object).
    """
    program_map = None
    reverse_program_map = None

    def __init__(self, emplid, adm_appl_nbr, app_stdnt_car_nbr, unit):
        self.emplid = emplid
        self.adm_appl_nbr = adm_appl_nbr
        self.app_stdnt_car_nbr = app_stdnt_car_nbr
        self.unit = unit
        self.happenings = []
        self.admit_term = None
        self.stdnt_car_nbr = None
        self.last_program = None

        self.gradstudent = None
        self.current_program = None # used to track program changes as we import
        self.student_info = None

        if not GradCareer.program_map:
            GradCareer.program_map = build_program_map()
        if not GradCareer.reverse_program_map:
            GradCareer.reverse_program_map = build_reverse_program_map()

    def __repr__(self):
        return "%s@%s:%s" % (self.emplid, self.adm_appl_nbr, self.stdnt_car_nbr)

    def add(self, h):
        """
        Add happening to this career, and maintain the metadata we need.
        """
        if h.adm_appl_nbr:
            if not self.adm_appl_nbr:
                self.adm_appl_nbr = h.adm_appl_nbr
            if self.stdnt_car_nbr is None:
                self.stdnt_car_nbr = h.stdnt_car_nbr

            if self.adm_appl_nbr != h.adm_appl_nbr or (h.stdnt_car_nbr is not None and self.stdnt_car_nbr != h.stdnt_car_nbr):
                raise ValueError

        assert h.unit == self.unit

        if hasattr(h, 'admit_term'):
            # record most-recent admit term we find
            self.admit_term = h.admit_term

        if isinstance(h, ProgramStatusChange):
            self.last_program = h.acad_prog

        self.happenings.append(h)
        h.in_career = True

    def sort_happenings(self):
        # sort ApplProgramChange after the corresponding ProgramStatusChange: let ProgramStatusChange win if they're on
        # the same day.
        self.happenings.sort(key=lambda h: (h.strm, h.effdt, 1 if isinstance(h, ApplProgramChange) else 0))

    def import_key(self):
        if self.adm_appl_nbr:
            adm_appl_nbr = self.adm_appl_nbr
        else:
            adm_appl_nbr = None
        return [self.emplid, adm_appl_nbr, self.unit.slug]

    def possibly_active_on(self, effdt):
        """
        Is this a date in which this career is conceivably active? i.e. might be taking courses or forming committees?
        """
        matr = [(h.effdt, h.admit_term) for h in self.happenings if isinstance(h, ProgramStatusChange) and h.prog_action in ['MATR', 'RADM']]
        # doing things happens after you are admitted (in the finally-selected admit_term).
        if not matr:
            return False
        matr_strm = max(matr)[1]
        matr_effdt = max(matr)[0]
        matr_dt = STRM_MAP[matr_strm].start
        if matr_dt > effdt:
            return False

        grads = [h.effdt for h in self.happenings if h.effdt >= matr_effdt and isinstance(h, ProgramStatusChange) and h.prog_status == 'CM']
        # can do things up to graduation day
        if grads:
            return effdt <= max(grads)

        ends = [h.effdt for h in self.happenings if h.effdt >= matr_effdt and isinstance(h, ProgramStatusChange) and h.prog_status in ['CN', 'DC']]
        if ends:
            # can't do things if you bailed
            end_dt = max(ends)
            return effdt < end_dt

        # ongoing program, so anything after admission
        return True

    def program_as_of(self, effdt):
        """
        What acad_prog is this career in as of effdt?
        """
        statuses = [h for h in self.happenings if isinstance(h, ProgramStatusChange) and h.effdt <= effdt]
        statuses.sort(key=lambda h: h.effdt)
        if statuses:
            return statuses[-1].acad_prog
        else:
            return None

    # program selection methods:
    def by_key(self, gs):
        return gs.config.get(SIMS_SOURCE, 'none') == self.import_key()

    def by_adm_appl_nbr(self, gs):
        return (gs.config.get('adm_appl_nbr', 'none') == self.adm_appl_nbr)

    def by_program_and_start(self, gs):
        return (self.last_program in GradCareer.reverse_program_map[gs.program]
                and gs.start_semester
                and gs.start_semester.name == self.admit_term)

    def by_similar_program_and_start(self, gs):
        return (self.last_program in GradCareer.reverse_program_map[gs.program]
                and gs.start_semester
                and gs.start_semester.offset_name(-2) <= self.admit_term <= gs.start_semester.offset_name(2)
                and 'adm_appl_nbr' not in gs.config and SIMS_SOURCE not in gs.config
        )

    def by_program_history(self, gs):
        gph = GradProgramHistory.objects.filter(student=gs, program=GradCareer.program_map[self.last_program], start_semester=gs.start_semester)
        return gph.exists()

    def by_hail_mary(self, gs):
        return (self.last_program in GradCareer.reverse_program_map[gs.program]
                and (not gs.start_semester
                    or gs.start_semester.offset_name(-4) <= self.admit_term <= gs.start_semester.offset_name(4))
                and 'adm_appl_nbr' not in gs.config and SIMS_SOURCE not in gs.config
        )

    # ways we have to find a matching GradStudent, in decreasing order of rigidness
    GS_SELECTORS = [ # (method_name, is_okay_to_find_multiple_matches?)
        ('by_key', False),
        ('by_adm_appl_nbr', False),
        ('by_program_and_start', True),
        ('by_similar_program_and_start', True),
        #('by_program_history', False),
        #('by_hail_mary', False),
    ]

    def find_gradstudent(self, verbosity, dry_run):
        gss = GradStudent.objects.filter(person__emplid=self.emplid, program__unit=self.unit).select_related('start_semester', 'program__unit')
        gss = list(gss)

        if self.admit_term < RELEVANT_PROGRAM_START:
            return

        for method, multiple_okay in GradCareer.GS_SELECTORS:
            by_selector = [gs for gs in gss if getattr(self, method)(gs)]
            #print method, by_selector
            if len(by_selector) == 1:
                return by_selector[0]
            elif len(by_selector) > 1:
                if multiple_okay:
                    return by_selector[-1]
                else:
                    raise ValueError, "Multiple records found by %s for %s." % (method, self)

        if GradCareer.program_map[self.last_program].unit.slug == 'cmpt' and self.admit_term < '1137':
            # Don't try to probe the depths of history for CMPT. You'll hurt yourself.
            # We have nice clean adm_appl_nbrs for 1137 onwards, so the reliable GS_SELECTORS will find the student
            return

        if verbosity:
            print "New grad student career found: %s/%s in %s starting %s." % (self.emplid, self.unit.slug, self.last_program, self.admit_term)

        # can't find anything in database: create new
        gs = GradStudent(person=add_person(self.emplid, commit=(not dry_run)))
        # everything else updated by gs.update_status_fields later

        gs.program = GradCareer.program_map[self.last_program] # ...but this is needed to save
        if not dry_run:
            gs.save() # get gs.id filled in for foreign keys elsewhere
        return gs

    def fill_gradstudent(self, verbosity, dry_run):
        gs = self.find_gradstudent(verbosity=verbosity, dry_run=dry_run)
        # be extra sure we aren't seeing multiple-unit GradStudent objects
        units = set(GradProgramHistory.objects.filter(student=gs).values_list('program__unit', flat=True))
        if len(units) > 1:
            if verbosity:
                raise ValueError, "Grad Student %s (%i) has programs in multiple units: that shouldn't be." % (gs.slug, gs.id)
        self.gradstudent = gs

    def update_local_data(self, verbosity, dry_run):
        """
        Update local data for the GradStudent using what we found in SIMS
        """
        # make sure we can find it easily next time
        self.gradstudent.config[SIMS_SOURCE] = self.import_key()
        if self.adm_appl_nbr:
            self.gradstudent.config['adm_appl_nbr'] = self.adm_appl_nbr

        # TODO: get_mother_tongue, get_passport_issued_by, holds_resident_visa, get_research_area, get_email from grad.management.commands.new_grad_student

        student_info = {
            'student': self.gradstudent,
            'statuses': list(GradStatus.objects.filter(student=self.gradstudent)
                .select_related('start').order_by('start__name', 'start_date')),
            'programs': list(GradProgramHistory.objects.filter(student=self.gradstudent)
                .select_related('start_semester', 'program').order_by('start_semester__name', 'starting')),
            'committee': list(Supervisor.objects.filter(student=self.gradstudent, removed=False) \
                .exclude(supervisor_type='POT')),
            'real_admit_term': self.admit_term,
        }
        self.student_info = student_info

        for h in self.happenings:
            # do this first for everything so a second pass can try harder to find things not matching in the first pass
            h.find_local_data(student_info, verbosity=verbosity)

        for h in self.happenings:
            h.update_local_data(student_info, verbosity=verbosity, dry_run=dry_run)

        # are there any GradProgramHistory objects happening before the student actually started (because they
        # deferred)? If so, defer them too.
        if self.unit.slug != 'cmpt':
            premature_gph = GradProgramHistory.objects.filter(student=self.gradstudent,
                                                              start_semester__name__lt=self.admit_term)
            for gph in premature_gph:
                gph.start_semester = STRM_MAP[self.admit_term]
                if verbosity:
                    print "Deferring program start for %s/%s to %s." % (self.emplid, self.unit.slug, self.admit_term)
                if not dry_run:
                    gph.save()

        if not dry_run:
            self.gradstudent.update_status_fields()
            self.gradstudent.save_if_dirty()


    def find_rogue_local_data(self, verbosity, dry_run):
        """
        Find any local data that doesn't seem to belong and report it.
        """
        extra_statuses = [s for s in self.student_info['statuses'] if SIMS_SOURCE not in s.config]
        extra_programs = [p for p in self.student_info['programs'] if SIMS_SOURCE not in p.config]
        extra_committee = [c for c in self.student_info['committee'] if SIMS_SOURCE not in c.config]
        if self.unit.slug == 'cmpt':
            # doesn't make sense for CMPT, since we're not importing everything else
            return

        if verbosity:
            for s in extra_statuses:
                print "Rogue grad status: %s was %s in %s" % (self.emplid, SHORT_STATUSES[s.status], s.start.name)
            for p in extra_programs:
                print "Rogue program change: %s in %s as of %s." % (self.emplid, p.program.slug, p.start_semester.name)
            for c in extra_committee:
                print "Rogue committee member: %s is a %s for %s" % (c.sortname(), SUPERVISOR_TYPE[c.supervisor_type], self.emplid)



def manual_cleanups(dry_run, verbosity):
    """
    These are ugly cleanups of old data that make the real import work well and leave less junk to clean later.
    """
    if dry_run:
        return

    # GradStudents that ended up split between units

    GradProgramHistory.objects.filter(student__id=4849, program__unit__slug='mse').delete()
    GradStatus.objects.filter(student__id=4849, status='GRAD').delete()
    GradStudent.objects.get(id=4849).update_status_fields()

    # ENSC -> CMPT and has real data from CMPT
    GradProgramHistory.objects.filter(student__id=2484, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=2484).update_status_fields()
    GradProgramHistory.objects.filter(student__id=2697, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=2697).update_status_fields()
    GradProgramHistory.objects.filter(student__id=535, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=535).update_status_fields()

    # rogue CMPT programhistory with no basis in SIMS
    GradProgramHistory.objects.filter(student__id=2417, program__unit__slug='cmpt').delete()
    GradStudent.objects.get(id=2417).update_status_fields()

    # ENSC -> MSE (where ENSC import already create the ENSC GradStudent: keep these for MSE)
    GradProgramHistory.objects.filter(student__id=4811, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4811).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4812, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4812).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4851, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4851).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4870, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4870).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4820, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4820).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4821, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4821).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4823, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4823).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4894, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4894).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4831, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4831).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4833, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4833).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4897, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4897).update_status_fields()
    GradProgramHistory.objects.filter(student__id=4839, program__unit__slug='ensc').delete()
    GradStudent.objects.get(id=4839).update_status_fields()

    GradProgramHistory.objects.filter(student__id=4817, program__unit__slug='ensc').delete()
    gs = GradStudent.objects.get(id=4817)
    gs.config['adm_appl_nbr'] = '00534543'
    gs.save()
    gs.update_status_fields()

    GradStudent.objects.get(id=5591).update_status_fields()
    GradStudent.objects.filter(id=10362).update(start_semester=STRM_MAP['1121'])

    # not-quite-right adm_appl_nbr from old import
    gs = GradStudent.objects.get(id=4770)
    gs.config['adm_appl_nbr'] = '00798960'
    gs.save()


def _batch_call(func, args, batchsize=500):
    for i in xrange(0, len(args), batchsize):
        batch = args[i:i+batchsize]
        yield func(batch)


def import_grads(dry_run, verbosity, import_emplids=None):
    prog_map = build_program_map()
    import_units = Unit.objects.filter(slug__in=IMPORT_UNIT_SLUGS)
    acad_progs = [acad_prog for acad_prog, program in prog_map.iteritems() if program.unit in import_units]

    # always do these: safe and rest of the import gets weird without them.
    manual_cleanups(verbosity=verbosity, dry_run=False)

    # Get the basic program data we need to generate a Timeline object (JSONable so we can throw it in celery later)
    # each entry is a tuple of ('ClassName', *init_args)
    timeline_data = defaultdict(list)
    for acad_prog in acad_progs:
        prog_changes = grad_program_changes(acad_prog)
        for p in prog_changes:
            emplid = p[1]
            d = timeline_data[emplid]
            d.append(p)

        # temporarily disable while we settle out everything else
        #appl_changes = grad_appl_program_changes(acad_prog)
        #for a in appl_changes:
        #    emplid = a[1]
        #    d = timeline_data[emplid]
        #    d.append(a)

    timeline_data = dict(timeline_data)

    if import_emplids:
        emplids = import_emplids
    else:
        emplids = sorted(timeline_data.keys())

    # fetch all of the grad/committee data now that we know who to fetch for
    for r in itertools.chain(*_batch_call(grad_semesters, emplids)):
        emplid = r[1]
        timeline_data[emplid].append(r)
    for r in itertools.chain(*_batch_call(committee_members, emplids)):
        emplid = r[1]
        timeline_data[emplid].append(r)

    for emplid in emplids:
        timeline = GradTimeline(emplid)
        data = timeline_data[emplid]
        for d in data:
            if d[0] == 'ProgramStatusChange':
                h = ProgramStatusChange(*(d[1:]))
            elif d[0] == 'ApplProgramChange':
                h = ApplProgramChange(*(d[1:]))
            elif d[0] == 'GradSemester':
                h = GradSemester(*(d[1:]))
            elif d[0] == 'CommitteeMembership':
                h = CommitteeMembership(*(d[1:]))
            else:
                raise ValueError, d[0]

            timeline.add(h)

        with transaction.atomic(): # all or nothing for each person
            timeline.split_careers(verbosity=verbosity)
            for c in timeline.careers:
                c.fill_gradstudent(verbosity=verbosity, dry_run=dry_run)
                if not c.gradstudent:
                    # we gave up on this because it's too old
                    continue
                c.update_local_data(verbosity=verbosity, dry_run=dry_run)
                #c.find_rogue_local_data(verbosity=verbosity, dry_run=dry_run)

            #timeline.find_rogue_local_data(verbosity=verbosity, dry_run=dry_run)








def find_true_home(obj, dry_run):
    """
    Find the true GradStudent where this object (on a rogue GradStudents) belongs.
    """
    old_gs = obj.student
    new_gss = list(GradStudent.objects.filter(person=old_gs.person, program=old_gs.program, config__contains=SIMS_SOURCE))
    if len(new_gss) > 2:
        raise ValueError, "Multiple matches for %s %s: please fix manually" % (old_gs.slug, obj.__class__.__name__)
    elif len(new_gss) == 0:
        raise ValueError, "No match for %s %s: please fix manually" % (old_gs.slug, obj.__class__.__name__)

    new_gs = new_gss[0]
    obj.student = new_gs
    if not dry_run:
        obj.save()

from grad.models import CompletedRequirement, Letter, Scholarship, OtherFunding, Promise, FinancialComment, GradFlagValue, ProgressReport, ExternalDocument
def rogue_grad_finder(unit_slug, dry_run=False, verbosity=1):
    """
    Examine grad students in this unit. Identify rogues that could be deleted.
    """
    # other things that could be found and possibly purged:
    # GradProgramHistory that's unconfirmed and to the program they're *already in*
    # GradStatus on-leave that's unconfirmed and in-the-past-enough that it's not a recent manual entry
    # There are Supervisors with external=='-None-' for CMPT: those can go.
    gss = GradStudent.objects.filter(program__unit__slug=unit_slug, start_semester__name__gte='1051')

    # what GradStudents haven't been found in SIMS?
    gs_unco = [gs for gs in gss if SIMS_SOURCE not in gs.config]

    # do the unconfirmed ones have any confirmed data associated? (implicitly ignoring manually-entered data on these fields)
    for GradModel in [GradProgramHistory, GradStatus, Supervisor]:
        res = [s.student.slug for s in GradModel.objects.filter(student__in=gs_unco) if SIMS_SOURCE in s.config]
        if res:
            raise ValueError, 'Found an unconfirmed %s for %s, who is rogue.' % (GradModel.__name__, s.student.slug)

    # do they have any other data entered manually?
    for GradModel in [CompletedRequirement, Letter, Scholarship, OtherFunding, Promise, FinancialComment, GradFlagValue, ProgressReport, ExternalDocument]:
        res = GradModel.objects.filter(student__in=gs_unco)
        #if res:
        #   raise ValueError, 'Found a %s for %s, who is rogue.' % (GradModel.__name__, s.student.slug)
        for r in res:
            find_true_home(r, dry_run=dry_run)

    if not dry_run:
        for gs in gs_unco:
            gs.current_status = 'DELE'
            gs.save()
