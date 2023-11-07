from .parameters import SIMS_SOURCE, DATE_OFFSET, DATE_OFFSET_START, RELEVANT_DATA_START, CMPT_CUTOFF
from .queries import metadata_translation_tables, research_translation_tables
from .tools import semester_lookup, STRM_MAP

from coredata.models import Unit
from coredata.queries import add_person
from grad.models import GradProgram, GradStatus, GradProgramHistory, Supervisor
from grad.models import STATUS_APPLICANT, SHORT_STATUSES, SUPERVISOR_TYPE

import datetime
from collections import defaultdict


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
        'PMSCS': GradProgram.objects.get(label="Prof MSc", unit=cmptunit),
        'CPMC': GradProgram.objects.get(label="Prof Msc Cybersec", unit=cmptunit),
        'CPMVC': GradProgram.objects.get(label="Prof Msc Visual Comp", unit=cmptunit),
        'CPPMS': GradProgram.objects.get(label="Prof MSc", unit=cmptunit),
    }
    engunit = Unit.objects.get(label="ENSC")
    mechunit = Unit.objects.get(label="MSE")
    program_map['MSEPH'] = GradProgram.objects.get(label="Ph.D.", unit=mechunit)
    program_map['MSEMS'] = GradProgram.objects.get(label="M.A.Sc.", unit=mechunit)
    program_map['MESMS'] = GradProgram.objects.get(label="M.Eng.", unit=mechunit)
    program_map['MSEGX'] = GradProgram.objects.get(label="GrExc", unit=mechunit)
    program_map['MECHVRS'] = GradProgram.objects.get(label="V.R.S.", unit=mechunit)
    program_map['ESMEN'] = GradProgram.objects.get(label="M.Eng.", unit=engunit)
    program_map['ESMAS'] = GradProgram.objects.get(label="M.A.Sc.", unit=engunit)
    program_map['ESPHD'] = GradProgram.objects.get(label="Ph.D.", unit=engunit)

    psychunit = Unit.objects.get(label='PSYC')
    program_map['PSGEX'] = GradProgram.objects.get(label="PSGEX", unit=psychunit)
    program_map['PSGND'] = GradProgram.objects.get(label="PSGND", unit=psychunit)
    program_map['PSGQL'] = GradProgram.objects.get(label="PSGQL", unit=psychunit)
    program_map['PSMAC'] = GradProgram.objects.get(label="PSMAC", unit=psychunit)
    program_map['PSMAP'] = GradProgram.objects.get(label="PSMAP", unit=psychunit)
    program_map['PSPHC'] = GradProgram.objects.get(label="PSPHC", unit=psychunit)
    program_map['PSPHP'] = GradProgram.objects.get(label="PSPHP", unit=psychunit)

    seeunit = Unit.objects.get(label="SEE")
    program_map['SEMAS'] = GradProgram.objects.get(label="SEE MASc", unit=seeunit)
    program_map['SEPHD'] = GradProgram.objects.get(label="SEE PhD", unit=seeunit)
    return program_map


def build_reverse_program_map():
    """
    Reverse of the program map, returning lists of acad_prog that *might* be the source of one of our programs.

    Needed because CMPT's flavours of masters aren't reflected in SIMS.
    """
    program_map = build_program_map()
    rev_program_map = defaultdict(list)
    for acad_prog, gradprog in list(program_map.items()):
        rev_program_map[gradprog].append(acad_prog)

    cmptunit = Unit.objects.get(label="CMPT")
    rev_program_map[GradProgram.objects.get(label="MSc Thesis", unit=cmptunit)].append('CPMSC')
    rev_program_map[GradProgram.objects.get(label="MSc Course", unit=cmptunit)].append('CPMCW')
    rev_program_map[GradProgram.objects.get(label="MSc Proj", unit=cmptunit)].append('CPMSC')
    return rev_program_map


def build_program_subplan_map():
    """
    Similar to build_program_map, but we now have some cases where we fake a GradProgram based on the program and
    subplan combination.
    :return: A dict of (program, subplan): GradProgram mapping.
    """
    cmptunit = Unit.objects.get(label="CMPT")
    program_subplan_map = {
        ('PMSCS', 'PMSCSBD'): GradProgram.objects.get(label="Prof MSc Big Data", unit=cmptunit),
        ('PMSCS', 'PMSCSVC'): GradProgram.objects.get(label="Prof MSc Visual Comp", unit=cmptunit),
        ('PMSCS', 'PMSCSCS'): GradProgram.objects.get(label="Prof MSc Cybersec", unit=cmptunit),
        ('CPMSC', 'CPMSCTHES'): GradProgram.objects.get(label="MSc Thesis", unit=cmptunit),
        ('CPMSC', 'CPMSCPROJ'): GradProgram.objects.get(label="MSc Proj", unit=cmptunit),
        ('CPMSC', 'CPMSCCRSW'): GradProgram.objects.get(label="MSc Course", unit=cmptunit),
    }
    return program_subplan_map


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



class GradHappening(object):
    """
    Superclass to represent things that happen to grad students.
    """
    program_map = None
    program_subplan_map = None
    def effdt_to_strm(self):
        "Look up the semester that goes with this date"
        # within a few days of the end of the semester, things applicable next semester are being entered
        offset = DATE_OFFSET
        if hasattr(self, 'status') and self.status == 'ACTI':
            offset = DATE_OFFSET_START
        elif isinstance(self, CommitteeMembership):
            offset = datetime.timedelta(days=0)

        if hasattr(self, 'status') and self.status in ['GRAD', 'GAPL', 'GAPR'] and self.exp_grad_term:
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

    def acad_prog_to_gradprogram(self, subplan=None):
        """
        Turn self.acad_prog into a GradProgram in self.grad_program if possible. Also set the unit that goes with it.
        """
        if GradHappening.program_map is None:
            GradHappening.program_map = build_program_map()

        if GradHappening.program_subplan_map is None:
            GradHappening.program_subplan_map = build_program_subplan_map()

        # If we got a subplan passed in, see if it matches one of our special cases where we fake the GradProgram
        # based on the subplan.  This should only apply to ProgramStatusChanges and ApplProgramChanges, as they are
        # the only things passing in this parameter.
        if subplan:
            found_subplan = False
            try:
                self.grad_program = GradHappening.program_subplan_map[(self.acad_prog, subplan)]
                self.unit = self.grad_program.unit
                found_subplan = True
            except KeyError:
                self.grad_program = None
                self.unit = None
            # If this worked, we're done, otherwise, do the logic based only on the program.
            if found_subplan:
                return

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
            prog_reason, effdt, effseq, admit_term, exp_grad_term, degr_chkout_stat, acad_sub_plan):
        # argument order must match grad_program_changes query
        self.emplid = emplid
        self.stdnt_car_nbr = None
        self.app_stdnt_car_nbr = stdnt_car_nbr
        self.adm_appl_nbr = adm_appl_nbr
        self.acad_prog = acad_prog
        self.effdt = effdt.date()
        self.admit_term = admit_term
        self.exp_grad_term = exp_grad_term

        self.prog_status = prog_status
        self.prog_action = prog_action
        self.prog_reason = prog_reason
        self.degr_chkout_stat = degr_chkout_stat

        self.status = self.prog_status_translate()
        self.acad_prog_to_gradprogram(subplan=acad_sub_plan)
        self.effdt_to_strm()

        # had to change sims_source status for these so ps_acad_prog and ps_adm_appl_prog results would identify
        self.oldkey = ['ps_acad_prog', emplid, effdt.isoformat(), self.prog_status, self.prog_reason, self.acad_prog,
                       self.prog_action]
        self.key = ['ps_acad_prog', emplid, effdt.isoformat(), self.prog_status, self.prog_reason, self.acad_prog,
                    self.prog_action, self.degr_chkout_stat]

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
        elif st_ac == ('AP', 'RAPP'):
            # application for readmission
            return 'COMP'
        elif st_ac == ('AP', 'DDEF'):
            # deferred decision: we don't represent that.
            return None
        elif st_ac == ('CN', 'WAPP'):
            return 'DECL'
        elif st_ac == ('CN', 'WADM'):
            # cancelled application
            return 'CANC'
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
        elif st_ac == ('AC', 'DATA'):
            # Application for graduation
            if self.degr_chkout_stat == 'AG':
                return 'GAPL'
            # Graduation status change to 'Approved'
            elif self.degr_chkout_stat == 'AP':
                return 'GAPR'
            # Some other data change that we most likely don't care about.
            return None

        elif self.prog_action == 'RECN':
            # "reconsideration"
            return None
        elif self.prog_action == 'DEFR':
            # deferred start: probably implies start semester change
            return 'DEFR'

        elif st_ac == ('WT', 'WAIT'):
            return 'WAIT'

        elif st_ac == ('AP', 'DATA') and self.prog_reason == 'WAIT':
            # Shows up in SIMS as 'Waitlisted by department', instead of the one above which is just 'Waitlisted'
            return 'WAIT'

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
        elif st_ac in [('DC', 'DISC'), ('DE', 'DISC')]:
            return 'WIDR'
        elif st_ac == ('LA', 'LEAV'):
            return 'LEAV'
        elif st_ac == ('AC', 'RLOA'):
            return 'ACTI'
        elif st_ac == ('AC', 'RADM'):
            return 'ACTI'
        elif st_ac == ('CM', 'COMP'):
            return 'GRAD'

        raise KeyError(str((self.emplid, self.prog_status, self.prog_action, self.prog_reason, self.degr_chkout_stat)))

    def import_key(self):
        return self.key
    def appl_key(self):
        return [self.strm, self.prog_status, self.prog_action, self.acad_prog]

    def status_config(self):
        "Additional entries for GradStatus.config when updating"
        return {}

    def find_same_appl_key(self, statuses):
        if self.status not in STATUS_APPLICANT:
            return None

        key = self.import_key()
        same_appl_key = [s for s in statuses
                if 'appl_key' in s.config and s.config['appl_key'] == self.appl_key()]
        if same_appl_key:
            #if len(same_appl_key) > 1:
            #    print(self.appl_key())
            #    print(same_appl_key)
            #    raise ValueError(str(key))
            s = same_appl_key[0]
            s.config[SIMS_SOURCE] = key
            assert s.status == self.status
            return s

    def find_existing_status(self, statuses, verbosity):
        # look for something previously imported from this record
        key = self.import_key()
        # ApplProgramChange can be the same as a ProgramStatusChange except different effdt: let the one sorted first
        # win, even if that means changing the sims_source (because ApplProgramChange has an earlier effdt, likely)
        s = self.find_same_appl_key(statuses)
        if s:
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
                print("* Found similar (but imperfect) status for %s/%s is %s in %s" % (self.emplid, self.unit.slug, self.status, self.strm))
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
                assert (st.start == STRM_MAP[self.strm]) or ('sims_source' in st.config and st.config['sims_source'] == self.import_key())


    def update_status(self, student_info, verbosity, dry_run):
        """
        Find/update GradStatus object for this happening
        """
        # don't manage for CMPT, except completed application status for recent applicants
        # if self.unit.slug == 'cmpt' and (self.status not in ['COMP', 'REJE'] or self.admit_term < CMPT_CUTOFF):
        #     return

        statuses = student_info['statuses']
        if self.gradstatus:
            st = self.gradstatus
        else:
            # try again by appl_key, in case we created one already (where an event is duplicated in ps_adm_appl_prog and ps_acad_prog)
            s = self.find_same_appl_key(statuses)
            if s:
                # TODO: what about next import? We'll oscillate?
                # we didn't find it before, but it's there now: just created it so let it be.
                return

            # try harder to find a local status we can use for this: anything close not found
            # by any find_local_data() call
            st = self.find_similar_status(statuses, verbosity=verbosity)
            if not st:
                # really not found: make a new one
                st = GradStatus(student=student_info['student'], status=self.status)
                statuses.append(st)
                if verbosity:
                    print("Adding grad status: %s/%s is '%s' as of %s." % (self.emplid, self.unit.slug, SHORT_STATUSES[self.status], self.strm))

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
                similar_history = [p for p in programs if p.start_semester.name == strm
                        and p.program == self.grad_program]
                if similar_history:
                    ph = similar_history[0]
                    #  We need to check if we have a different date for this action than the matching entry.
                    #  in some cases (like adding an active status afterwards), we need this date to be maximized
                    #  to show the correct current program.
                    if ph.starting != self.effdt:
                        if verbosity > 1:
                            print("Changing start of similar program %s/%s in %s from %s to %s" % \
                                  (self.emplid, self.unit.slug, self.grad_program.slug, ph.starting, self.effdt))
                        ph.starting = self.effdt
                        if not dry_run:
                            ph.save()

                else:
                    need_ph = True

        else:
            # maybe the next-known program change is to the same program? If so, move it back.
            next_history = [p for p in programs if p.start_semester.name > strm]
            if next_history and next_history[0].program == self.grad_program:
                if verbosity > 1:
                    print("* Adjusting program change start: %s/%s in %s as of %s." % (self.emplid, self.unit.slug, self.grad_program.slug, strm))
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
                print("Adding program change: %s/%s in %s as of %s." % (self.emplid, self.unit.slug, self.grad_program.slug, strm))
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
        # if self.grad_program.unit.slug == 'cmpt':
        #     return

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
                print("* Adjusting date of grad status: %s/%s is '%s' as of %s (was taking courses)." % (self.emplid, self.unit.slug, SHORT_STATUSES['ACTI'], self.strm))

            st.start_date = effdt
            st.config[SIMS_SOURCE] = key
            if not dry_run:
                st.save()
        else:
            # Option 3: need to add an active status
            if verbosity:
                print("Adding grad status: %s/%s is '%s' as of %s (was taking courses)." % (self.emplid, self.unit.slug, SHORT_STATUSES['ACTI'], self.strm))
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
        self.effdt = effdt.date()
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
        return "%s as %s for %s in %s" % (self.sup_emplid, self.committee_role, self.emplid, self.acad_prog)

    def find_local_data(self, student_info, verbosity):
        pass

    def import_key(self):
        return [self.committee_id, self.effdt.isoformat(), self.committee_type, self.sup_emplid, self.committee_role]

    def update_local_data(self, student_info, verbosity, dry_run):
        # if self.grad_program.unit.slug == 'cmpt':
        #     return

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
                    print("* Found similar (but imperfect) committee member for %s is a %s for %s/%s" % (p.name(), SUPERVISOR_TYPE[sup_type], self.emplid, self.unit.slug))
                member = similar[0]
            else:
                if verbosity:
                    print("Adding committee member: %s is a %s for %s/%s" % (p.name(), SUPERVISOR_TYPE[sup_type], self.emplid, self.unit.slug))
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
        return ['unit_change_'+self.inout(), self.emplid, self.adm_appl_nbr, self.effdt.isoformat(), self.unit.slug, self.otherunit.slug]

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


class GradResearchArea(GradHappening):
    """
    The research area given by this student on his/her application.

    There may be several of these: they end up joined together into a text field.
    """
    trans_areas, trans_choices, trans_acad_org = None, None, None
    def __init__(self, emplid, adm_appl_nbr, acad_org, area, choice):
        if not GradResearchArea.trans_areas:
            GradMetadata.trans_areas, GradMetadata.trans_choices = research_translation_tables()
            units = Unit.objects.exclude(acad_org__isnull=True).exclude(acad_org='')
            GradResearchArea.trans_acad_org = dict((u.acad_org, u) for u in units)

        self.emplid = emplid
        self.adm_appl_nbr = adm_appl_nbr
        self.acad_org = acad_org
        self.area = area
        self.choice = choice

        self.unit = GradResearchArea.trans_acad_org.get(acad_org, None)

        # sort them last so careers are made by acad_prog happenings, not this.
        self.strm = '9999'
        self.effdt = datetime.date(3000, 1, 1)
        self.grad_program = True
        self.stdnt_car_nbr = None
        self.in_career = False

    def find_local_data(self, student_info, verbosity):
        pass

    def update_local_data(self, student_info, verbosity, dry_run):
        # collect the research areas in the career, so they're all together
        career = student_info['career']
        ch = GradMetadata.trans_choices.get((self.acad_org, self.area, self.choice), None)
        if ch:
            career.research_areas.add(ch)


class GradMetadata(GradHappening):
    """
    Information about the person: this applies to all Careers for this person.

    Not really treated like other happenings: becomes Career.metadata, not one of its happenings.
    """
    trans_lang, trans_countries, trans_visas = None, None, None
    def __init__(self, emplid, email, lang, citizen, visa, _, s1, s2):
        if not GradMetadata.trans_lang:
            GradMetadata.trans_lang, GradMetadata.trans_countries, GradMetadata.trans_visas = metadata_translation_tables()

        self.emplid = emplid
        self.email = email
        self.lang = GradMetadata.trans_lang.get(lang, None)
        self.citcode = citizen
        self.citizen = GradMetadata.trans_countries.get(citizen, None)
        vstatus, self.visa = GradMetadata.trans_visas.get(visa, (None, None))

        self.strm = '0000'
        self.effdt = datetime.date(1900, 1, 1)
        self.grad_program = None

        # they're Canadian for employment purposes if they're a citizen or on a 'resident' visa
        self.is_canadian = self.citcode == 'CAN' or vstatus == 'R'

    def update_local_data(self, gs, verbosity, dry_run):
        changed = []

        # keep the first ever non-SFU preferred email as their applic_email
        if self.email and not self.email.endswith('@sfu.ca') and not gs.config.get('applic_email', None):
            gs.config['applic_email'] = self.email
            changed.append('application email address')

        # keep the most-recently found non-null for the other fields

        if self.lang and self.lang != gs.mother_tongue:
            gs.mother_tongue = self.lang
            changed.append('language')

        if self.citizen and self.citizen != gs.passport_issued_by:
            gs.passport_issued_by = self.citizen
            changed.append('citizenship')

        if self.visa and self.visa != gs.person.config.get('visa', None):
            gs.person.config['visa'] = self.visa
            changed.append('visa')

        if self.is_canadian != gs.is_canadian:
            gs.is_canadian = self.is_canadian
            changed.append('Canadianness')


        if changed:
            if verbosity > 1:
                print("* Changed personal info for %s/%s: %s" % (self.emplid, gs.program.unit.slug, ', '.join(changed)))
            if not dry_run:
                gs.save()
                if 'visa' in changed:
                    gs.person.save()


