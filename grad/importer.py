from django.db import transaction
from django.conf import settings
from coredata.queries import add_person, SIMSConn, SIMS_problem_handler, cache_by_args, get_supervisory_committee
from coredata.models import Semester, Unit
from grad.models import GradProgram, GradStudent, Supervisor, GradStatus, GradProgramHistory
from grad.models import STATUS_APPLICANT, SHORT_STATUSES, SUPERVISOR_TYPE
import datetime
from collections import defaultdict
from pprint import pprint
import intervaltree

# TODO: some Supervisors were imported from cortez as external with "userid@sfu.ca". Ferret them out
# TODO: adjust LEAV statuses depending on the NWD/WRD status from ps_stdnt_car_term?
# TODO: GradStudent.create does things: use it
# TODO: CMPT distinction between thesis/project/course in SIMS?

# in ps_acad_prog dates within about this long of the semester start are actually things that happen next semester
DATE_OFFSET = datetime.timedelta(days=30)
# ...even longer for dates of things that are startup-biased (like returning from leave)
DATE_OFFSET_START = datetime.timedelta(days=90)
ONE_DAY = datetime.timedelta(days=1)

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
    db = SIMSConn()
    db.execute("""
        SELECT emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action, prog_reason,
            effdt, effseq, admit_term, exp_grad_term
        FROM ps_acad_prog
        WHERE acad_career='GRAD' AND acad_prog=%s AND effdt>=%s AND admit_term>=%s
        ORDER BY effdt, effseq
    """, (acad_prog, IMPORT_START_DATE, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def grad_semesters(emplid):
    db = SIMSConn()
    db.execute("""
        SELECT emplid, strm, stdnt_car_nbr, withdraw_code, acad_prog_primary, unt_taken_prgrss
        FROM ps_stdnt_car_term
        WHERE acad_career='GRAD' AND emplid=%s AND strm>=%s
            AND unt_taken_prgrss>0
        ORDER BY strm
    """, (emplid, IMPORT_START_SEMESTER))
    return list(db)

@SIMS_problem_handler
@cache_by_args
def committee_members(emplid):
    db = SIMSConn()
    db.execute("""
        SELECT st.emplid, st.committee_id, st.acad_prog, com.effdt, com.committee_type, mem.emplid, mem.committee_role
        FROM
            ps_stdnt_advr_hist st
            JOIN ps_committee com
                ON (com.institution=st.institution AND com.committee_id=st.committee_id)
            JOIN ps_committee_membr mem
                ON (mem.institution=st.institution AND mem.committee_id=st.committee_id AND com.effdt=mem.effdt)
        WHERE
            st.emplid=%s
        ORDER BY com.effdt""",
        (emplid,))
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
    program_map = build_program_map()
    rev_program_map = defaultdict(list)
    for acad_prog, gradprog in program_map.items():
        rev_program_map[gradprog].append(acad_prog)

    cmptunit = Unit.objects.get(label="CMPT")
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

        if hasattr(self, 'status') and self.status == 'GRAD':
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
        if GradHappening.program_map is None:
            GradHappening.program_map = build_program_map()

        try:
            self.grad_program = GradHappening.program_map[self.acad_prog]
        except KeyError:
            self.grad_program = None


class ProgramStatusChange(GradHappening):
    def __init__(self, emplid, stdnt_car_nbr, adm_appl_nbr, acad_prog, prog_status, prog_action,
            prog_reason, effdt, effseq, admit_term, exp_grad_term):
        # argument order must match grad_program_changes query
        self.emplid = emplid
        self.stdnt_car_nbr = None # these seem meaningless
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

        self.key = ['ps_acad_prog', emplid, 'GRAD', stdnt_car_nbr, effdt, effseq]

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
        # must be JSON-serializable (and comparable for equality after serializing/deserializing)
        return self.key

    def find_existing_status(self, statuses, verbosity):
        # look for something previously imported from this
        key = self.import_key()
        existing = [s for s in statuses
                if 'sims_source' in s.config and s.config['sims_source'] == key]
        if existing:
            assert existing[0].status == self.status
            return existing[0]

        # look for a real match in old data
        similar = [s for s in statuses
                if s.start.name == self.strm
                and s.status == self.status
                and 'sims_source' not in s.config]

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
                and 'sims_source' not in s.config
                and not hasattr(s, 'found_in_import')]
        if close_enough:
            if verbosity > 2:
                print "* Found similar (but imperfect) status for %s is %s in %s" % (self.emplid, self.status, self.strm)
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


    def update_local_data(self, student_info, verbosity, dry_run):
        # grad status
        if self.status:
            statuses = student_info['statuses']
            if self.gradstatus:
                st = self.gradstatus
            else:
                # try really hard to find a local status we can use for this: anything close not found
                # by any find_local_data() call
                st = self.find_similar_status(statuses, verbosity=verbosity)
                if not st:
                    # really not found: make a new one
                    st = GradStatus(student=student_info['student'], status=self.status)
                    statuses.append(st)
                    if verbosity:
                        print "Adding grad status: %s is '%s' as of %s." % (self.emplid, SHORT_STATUSES[self.status], self.strm)

            self.gradstatus = st
            self.gradstatus.found_in_import = True

            assert st.status == self.status
            st.start = STRM_MAP[self.strm]
            st.start_date = self.effdt
            st.config['sims_source'] = self.import_key()

            if not dry_run:
                st.save_if_dirty()

            # re-sort if we added something, so we find things right on the next check
            student_info['statuses'].sort(key=lambda ph: (ph.start.name, ph.start_date or datetime.date(1900,1,1)))

        # program history
        programs = student_info['programs']
        previous_history = [p for p in programs if p.start_semester.name <= self.strm]
        need_ph = False
        if previous_history:
            # there is a previously-know program: make sure it matches
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
            # no history: create
            need_ph = True

        key = self.import_key()
        existing_history = [p for p in programs if
                'sims_source' in p.config and p.config['sims_source'] == key]
        if existing_history:
            need_ph = False

        if need_ph:
            if (verbosity and previous_history) or verbosity > 1:
                # don't usually report first ever ProgramHistory because those are boring
                print "Adding program change: %s in %s as of %s." % (self.emplid, self.grad_program.slug, self.strm)
            ph = GradProgramHistory(student=student_info['student'], program=self.grad_program,
                    start_semester=STRM_MAP[self.strm], starting=self.effdt)
            ph.config['sims_source'] = key
            student_info['programs'].append(ph)
            student_info['programs'].sort(key=lambda p: (p.start_semester.name, p.starting))
            if not dry_run:
                ph.save()
        else:
            if 'sims_source' not in ph.config:
                ph.config['sims_source'] = key
                if not dry_run:
                    ph.save()




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
        self.acad_prog = acad_prog_primary
        self.unt_taken_prgrss = unt_taken_prgrss

        self.acad_prog_to_gradprogram()

        self.adm_appl_nbr = None
        self.in_career = False

    def __repr__(self):
        return "%s in %s" % (self.withdraw_code, self.strm)

    def key(self):
        return ['ps_stdnt_car_term', self.emplid, self.strm]

    def find_local_data(self, student_info, verbosity):
        pass

    def update_local_data(self, student_info, verbosity, dry_run):
        # make sure the student is "active" as of the start of this semester, since they're taking courses
        statuses = student_info['statuses']
        semester = STRM_MAP[self.strm]
        effdt = semester.start
        key = self.key()

        # Option 1: we're already active
        effective_statuses = [s for s in statuses if s.start.name <= self.strm
                and (not s.start_date or s.start_date <= effdt)]
        if effective_statuses and effective_statuses[-1].status == 'ACTI':
            s = effective_statuses[-1]
            if 'sims_source' not in s.config:
                s.config['sims_source'] = key
                if not dry_run:
                    s.save()
            return

        # Option 2: there's an active status this semester, but it's not the most recent
        active_semester_statuses = [s for s in statuses if s.start.name == self.strm and s.status == 'ACTI']

        if active_semester_statuses:
            if verbosity > 1:
                print "* Adjusting date of grad status: %s is '%s' as of %s (was taking courses)." % (self.emplid, SHORT_STATUSES['ACTI'], self.strm)
            st = active_semester_statuses[-1]
            st.start_date = effdt
            st.config['sims_source'] = key
            if not dry_run:
                st.save()
        else:
            # Option 3: need to add an active status
            if verbosity:
                print "Adding grad status: %s is '%s' as of %s (was taking courses)." % (self.emplid, SHORT_STATUSES['ACTI'], self.strm)
            st = GradStatus(student=student_info['student'], status='ACTI', start=semester,
                    start_date=effdt)
            st.config['sims_source'] = key
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
        return "%s as %s" % (self.sup_emplid, self.committee_role)

    def find_local_data(self, student_info, verbosity):
        pass

    def update_local_data(self, student_info, verbosity, dry_run):
        key = [self.committee_id, self.effdt, self.committee_type, self.sup_emplid, self.committee_role]
        local_committee = student_info['committee']
        sup_type = COMMITTEE_MEMBER_MAP[self.committee_role]

        # should we be checking that the current local program and the committee program match up?
        #print self.grad_program, student_info['student'].program_as_of(STRM_MAP[self.strm])

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
                    print "* Found similar (but imperfect) committee member for %s is a %s for %s" % (p.name(), SUPERVISOR_TYPE[sup_type], self.emplid)
                member = similar[0]
            else:
                if verbosity:
                    print "Adding committee member: %s is a %s for %s" % (p.name(), SUPERVISOR_TYPE[sup_type], self.emplid)
                member = Supervisor(student=student_info['student'], supervisor=p, supervisor_type=sup_type)
                member.created_at = self.effdt
                local_committee.append(member)

        if 'sims_source' not in member.config:
            # record (the first) place we found this fact
            member.config['sims_source'] = key
            # if it wasn't the product of a previous import it was hand-entered: take the effdt from SIMS
            member.created_at = self.effdt

        # TODO: try to match up external members with new real ones? That sounds hard.
        # TODO: remove members if added by this import (in the past) and not found

        if not dry_run:
            member.save_if_dirty()



class GradTimeline(object):
    def __init__(self, emplid, unit):
        self.emplid = emplid
        self.unit = unit
        self.happenings = []
        self.careers = []

    def __repr__(self):
        return 'GradTimeline(%s, %s)' % (self.emplid, repr(self.happenings))

    def add(self, happening):
        self.happenings.append(happening)

    def add_semester_happenings(self):
        for gs in grad_semesters(self.emplid):
            h = GradSemester(*gs)
            self.add(h)

    def add_committee_happenings(self):
        for cm in committee_members(self.emplid):
            h = CommitteeMembership(*cm)
            self.add(h)

    def split_careers(self, verbosity=1):
        """
        Take all of the happenings we found and split them into careers, with each representing one GradStudent object.

        Rules:
        careers have to be within one unit
        a career is usually started by applying for a program (or by transferring between units)
        """
        # TODO: if we find multiple careeers with the same adm_appl_nbr (because of intra-unit transfer), create some "transferred out" and "transferred in" statuses
        # pass 1: we know the adm_appl_nbr
        for h in self.happenings:
            if not h.grad_program:
                continue

            if h.adm_appl_nbr:
                cs = [c for c in self.careers if c.unit == h.grad_program.unit and c.adm_appl_nbr == h.adm_appl_nbr]
                if len(cs) == 1:
                    c = cs[0]
                else:
                    c = GradCareer(self.emplid, h.adm_appl_nbr, h.grad_program.unit)
                    self.careers.append(c)

                c.add(h)
                h.in_career = True

        # pass 2: look at admit_term
        for h in self.happenings:
            if h.in_career or not h.grad_program:
                continue

            possible_careers = [c for c in self.careers if c.unit == h.grad_program.unit and c.admit_term <= h.strm]
            if not possible_careers:
                continue

            possible_careers.sort(key=lambda c: c.admit_term)
            c = possible_careers[-1]
            c.check_stdnt_car_nbr(h)
            c.add(h)
            h.in_career = True

        # pass 3: look at first_admit_term: some stdnt_car_terms happen but then they defer their start
        for h in self.happenings:
            if h.in_career or not h.grad_program:
                continue

            possible_careers = [c for c in self.careers if c.unit == h.grad_program.unit and c.first_admit_term <= h.strm]
            if not possible_careers:
                continue

            possible_careers.sort(key=lambda c: c.admit_term)
            c = possible_careers[-1]
            c.add(h)
            h.in_career = True

        # Failures to categorize happenings into a career by this point seem to always have to do with an
        # older career that we're not importing. Those get dropped here.

        for c in self.careers:
            c.sort_happenings()

    def find_rogue_local_data(self, verbosity, dry_run):
        existing_grads = set(GradStudent.objects.filter(program__unit=self.unit, person__emplid=self.emplid, start_semester__name__gt=RELEVANT_PROGRAM_START).select_related('start_semester', 'program__unit'))
        found_grads = set(c.gradstudent for c in self.careers if c.gradstudent and c.gradstudent.id)
        extra_grads = existing_grads - found_grads
        if verbosity:
            for gs in extra_grads:
                if 'sims_source' in gs.config:
                    # trust us-from-the-past
                    continue
                print 'Rogue grad student: %s in %s starting %s' % (self.emplid, gs.program.slug, gs.start_semester.name if gs.start_semester else '???')




class GradCareer(object):
    program_map = None
    reverse_program_map = None

    def __init__(self, emplid, adm_appl_nbr, unit):
        self.emplid = emplid
        self.adm_appl_nbr = adm_appl_nbr
        self.unit = unit
        self.happenings = []
        self.admit_term = None
        self.first_admit_term = None
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
        if h.adm_appl_nbr:
            if not self.adm_appl_nbr:
                self.adm_appl_nbr = h.adm_appl_nbr
            if not self.stdnt_car_nbr:
                self.stdnt_car_nbr = h.stdnt_car_nbr

            if self.adm_appl_nbr != h.adm_appl_nbr or (h.stdnt_car_nbr and self.stdnt_car_nbr != h.stdnt_car_nbr):
                raise ValueError

        assert h.grad_program.unit == self.unit

        if hasattr(h, 'admit_term'):
            # record earliest-ever-proposed admit term we find
            if self.first_admit_term is None or self.first_admit_term > h.admit_term:
                self.first_admit_term = h.admit_term

        if hasattr(h, 'admit_term'):
            # record most-recent admit term we find
            self.admit_term = h.admit_term

        self.last_program = h.acad_prog

        self.happenings.append(h)

    def sort_happenings(self):
        self.happenings.sort(key=lambda h: h.strm)

    def import_key(self):
        assert self.adm_appl_nbr
        return [self.emplid, self.adm_appl_nbr, self.unit.slug]

    def check_stdnt_car_nbr(self, h):
        if not self.stdnt_car_nbr and h.stdnt_car_nbr:
            self.stdnt_car_nbr = h.stdnt_car_nbr
        #elif self.stdnt_car_nbr and h.stdnt_car_nbr and self.stdnt_car_nbr != h.stdnt_car_nbr:
        #    raise ValueError

    # program selection methods:
    def by_key(self, gs):
        return gs.config.get('sims_source', 'none') == self.import_key()

    def by_adm_appl_nbr(self, gs):
        return gs.config.get('adm_appl_nbr', 'none') == self.adm_appl_nbr

    def by_program_and_start(self, gs):
        return (GradCareer.program_map[self.last_program] == gs.program
                and gs.start_semester
                and gs.start_semester.name == self.admit_term)

    def by_similar_program_and_start(self, gs):
        return (self.last_program in GradCareer.reverse_program_map[gs.program]
                and gs.start_semester
                and gs.start_semester.offset_name(-2) <= self.admit_term <= gs.start_semester.offset_name(2)
        )

    GS_SELECTORS = [ # (method_name, is_okay_to_find_multiple_matches?)
        ('by_key', False),
        ('by_adm_appl_nbr', True),
        ('by_program_and_start', True),
        ('by_similar_program_and_start', True),
    ]

    def find_gradstudent(self, verbosity, dry_run):
        gss = GradStudent.objects.filter(person__emplid=self.emplid).select_related('start_semester', 'program__unit')
        gss = list(gss)

        if self.admit_term < RELEVANT_PROGRAM_START:
            return

        for method, multiple_okay in GradCareer.GS_SELECTORS:
            by_selector = [gs for gs in gss if getattr(self, method)(gs)]
            if len(by_selector) == 1:
                return by_selector[0]
            elif len(by_selector) > 1:
                if multiple_okay:
                    return by_selector[-1]
                else:
                    raise ValueError, "Multiple records found by %s for %s." % (method, self)

        if verbosity:
            print "New grad student career found: %s in %s starting %s." % (self.emplid, self.last_program, self.admit_term)

        # can't find anything in database: create new
        gs = GradStudent(person=add_person(self.emplid, commit=(not dry_run)))
        # everything else updated by gs.update_status_fields later

        gs.program = GradCareer.program_map[self.last_program] # ...but this is needed to save
        if not dry_run:
            gs.save() # get gs.id filled in for foreign keys elsewhere
        return gs

    def fill_gradstudent(self, verbosity, dry_run):
        gs = self.find_gradstudent(verbosity=verbosity, dry_run=dry_run)
        self.gradstudent = gs

    def update_local_data(self, verbosity, dry_run):
        """
        Update local data for the GradStudent using what we found in SIMS
        """
        # make sure we can find it next time
        self.gradstudent.config['sims_source'] = self.import_key()
        if self.adm_appl_nbr:
            self.gradstudent.config['adm_appl_nbr'] = self.adm_appl_nbr

        student_info = {
            'student': self.gradstudent,
            'statuses': list(GradStatus.objects.filter(student=self.gradstudent)
                .select_related('start').order_by('start__name', 'start_date')),
            'programs': list(GradProgramHistory.objects.filter(student=self.gradstudent)
                .select_related('start_semester', 'program').order_by('start_semester__name', 'starting')),
            'committee': list(Supervisor.objects.filter(student=self.gradstudent, removed=False) \
                .exclude(supervisor_type='POT')),
        }
        self.student_info = student_info

        #print "  ", self.emplid, self.adm_appl_nbr, self.unit.slug, self.admit_term, self.gradstudent

        for h in self.happenings:
            # do this first for everything so a second pass can try harder to find things not matching in the first pass
            h.find_local_data(student_info, verbosity=verbosity)

        for h in self.happenings:
            h.update_local_data(student_info, verbosity=verbosity, dry_run=dry_run)

        if not dry_run:
            self.gradstudent.update_status_fields()
            self.gradstudent.save_if_dirty()


    def find_rogue_local_data(self, verbosity, dry_run):
        """
        Find any local data that doesn't seem to belong and report it.
        """
        extra_statuses = [s for s in self.student_info['statuses'] if 'sims_source' not in s.config]
        extra_programs = [p for p in self.student_info['programs'] if 'sims_source' not in p.config]
        extra_committee = [c for c in self.student_info['committee'] if 'sims_source' not in c.config]
        if verbosity:
            for s in extra_statuses:
                print "Rogue grad status: %s was %s in %s" % (self.emplid, SHORT_STATUSES[s.status], s.start.name)
            for p in extra_programs:
                print "Rogue program change: %s in %s as of %s." % (self.emplid, p.program.slug, p.start_semester.name)
            for c in extra_committee:
                print "Rogue committee member: %s is a %s for %s" % (c.sortname(), SUPERVISOR_TYPE[c.supervisor_type], self.emplid)






def import_unit_grads(unit, dry_run, verbosity):
    prog_map = build_program_map()
    acad_progs = [acad_prog for acad_prog, program in prog_map.iteritems() if program.unit == unit]

    timelines = {}
    for acad_prog in acad_progs:
        appls = grad_program_changes(acad_prog)
        for a in appls:
            emplid = a[0]
            timeline = timelines.get(emplid, None)
            if not timeline:
                timeline = GradTimeline(emplid, unit)
                timelines[emplid] = timeline
            status = ProgramStatusChange(*a)
            timeline.add(status)


    emplids = sorted(timelines.keys())
    for emplid in emplids:
        if emplid not in timelines:
            continue

        timeline = timelines[emplid]
        timeline.add_semester_happenings()
        timeline.add_committee_happenings()
        timeline.split_careers(verbosity=verbosity)
        with transaction.atomic(): # all or nothing for each person
            for c in timeline.careers:
                c.fill_gradstudent(verbosity=verbosity, dry_run=dry_run)
                if not c.gradstudent:
                    # we gave up on this because it's too old
                    continue
                if c.gradstudent.program.unit != unit:
                    # only touch if it's from the unit we're trying to import
                    continue
                c.update_local_data(verbosity=verbosity, dry_run=dry_run)
                c.find_rogue_local_data(verbosity=verbosity, dry_run=dry_run)

            timeline.find_rogue_local_data(verbosity=verbosity, dry_run=dry_run)



def find_true_home(obj, dry_run):
    """
    Find the true GradStudent where this object (on a rogue GradStudents) belongs.
    """
    old_gs = obj.student
    new_gss = list(GradStudent.objects.filter(person=old_gs.person, program=old_gs.program, config__contains='sims_source'))
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
    gss = GradStudent.objects.filter(program__unit__slug=unit_slug, start_semester__name__gte='1051')

    # what GradStudents haven't been found in SIMS?
    gs_unco = [gs for gs in gss if 'sims_source' not in gs.config]

    # do the unconfirmed ones have any confirmed data associated? (implicitly ignoring manually-entered data on these fields)
    for GradModel in [GradProgramHistory, GradStatus, Supervisor]:
        res = [s.student.slug for s in GradModel.objects.filter(student__in=gs_unco) if 'sims_source' in s.config]
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
