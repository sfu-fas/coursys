from .parameters import IMPORT_START_DATE, RELEVANT_PROGRAM_START, SIMS_SOURCE
from .career import GradCareer
from .happenings import ProgramStatusChange, CommitteeMembership, GradSemester, ApplProgramChange, CareerUnitChangeIn,\
    CareerUnitChangeOut, GradMetadata, GradResearchArea

from grad.models import GradStudent
import datetime, itertools

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
            if isinstance(h, ApplProgramChange) and h.unit.slug != 'cmpt':
                # other units don't care as much about applicants here: temporarily disable
                h.in_career = True
                continue

            if h.adm_appl_nbr and h.unit:
                cs = [c for c in self.careers if c.unit == h.unit and c.adm_appl_nbr == h.adm_appl_nbr]
                if len(cs) > 1:
                    raise ValueError(str(cs))
                elif len(cs) == 1:
                    c = cs[0]
                elif not isinstance(h, GradResearchArea): # don't let research area entries create careers: just toss.
                    c = GradCareer(self.emplid, h.adm_appl_nbr, h.app_stdnt_car_nbr, h.unit)
                    self.careers.append(c)
                else: #... and ignore research areas if there's no career for them by now. *Only* match by adm_appl_nbr.
                    assert isinstance(h, GradResearchArea)
                    h.in_career = True
                    continue

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
                        raise ValueError("Multiple career options for happening %s for %s. %s" % (h, self.emplid, possible_careers))
                else:
                    # make sure that "active program" filter didn't cause an inappropriate new career
                    assert h.prog_action not in ['LEAV', 'RLOA', 'DISC', 'COMP']

                    # it's a new career, conjured out of the ether

            if not h.in_career:
                # no existing program: must be new.
                c = GradCareer(self.emplid, h.adm_appl_nbr, h.app_stdnt_car_nbr, h.grad_program.unit)
                self.careers.append(c)
                c.add(h)

        # pass 2.5: put GradMetadata happenings in *every* career since they're about the person, not program
        for h in self.happenings:
            if not isinstance(h, GradMetadata):
                continue

            for c in self.careers:
                c.metadata = h
            # the first row found should win because of the sort order
            break

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
                    if not h.in_career and (isinstance(h, CommitteeMembership) or isinstance(h, GradResearchArea)):
                        # Committee member added to one program after student changed to another: drop this one.
                        # Committee membership for student's new program should be in another happening.
                        # Research areas where we didn't find any other info can be dropped.
                        h.in_career = True
                    elif not h.in_career and isinstance(h, GradSemester) and h.effdt - datetime.timedelta(days=730) < IMPORT_START_DATE:
                        # student in classes just after the beginning of time: we missed the career
                        h.in_career = True



        dropped = [h for h in happenings if not h.in_career]
        if dropped:
            raise ValueError('Some happenings got dropped for %s! %s' % (self.emplid, dropped))

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
                if isinstance(h, ApplProgramChange) and (h.prog_status, h.prog_action) == ('AP', 'APPL') and c.admit_term < '1157':
                    c.application_only = True

        self.careers = [c for c in self.careers if not c.application_only]

    def find_rogue_local_data(self, verbosity, dry_run):
        """
        Look for things in the local data that don't seem to match reality.
        """
        # if self.unit.slug == 'cmpt':
        #     # don't worry about these for now
        #     return

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
                print('Rogue grad student: %s in %s starting %s' % (self.emplid, gs.program.slug, gs.start_semester.name if gs.start_semester else '???'))
