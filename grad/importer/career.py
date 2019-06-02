from .parameters import SIMS_SOURCE, RELEVANT_PROGRAM_START, CMPT_CUTOFF
from .happenings import build_program_map, build_reverse_program_map
from .happenings import ProgramStatusChange, ApplProgramChange, GradResearchArea
from .tools import STRM_MAP

from coredata.queries import add_person
from grad.models import GradStudent, GradProgramHistory, GradStatus, Supervisor, SHORT_STATUSES, SUPERVISOR_TYPE

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
        self.metadata = None
        self.research_areas = set()

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
        if h.adm_appl_nbr and not isinstance(h, GradResearchArea):
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
                and gs.start_semester.name == self.admit_term
                and 'adm_appl_nbr' not in gs.config and SIMS_SOURCE not in gs.config)

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
        gss = GradStudent.objects.filter(person__emplid=self.emplid, program__unit=self.unit).select_related('start_semester', 'program__unit', 'person')
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
                    raise ValueError("Multiple records found by %s for %s." % (method, self))

        if GradCareer.program_map[self.last_program].unit.slug == 'cmpt' and self.admit_term < CMPT_CUTOFF:
            # Don't try to probe the depths of history for CMPT. You'll hurt yourself.
            # We have nice clean adm_appl_nbrs for CMPT_CUTOFF onwards, so the reliable GS_SELECTORS will find the student
            return

        if verbosity:
            print("New grad student career found: %s/%s in %s starting %s." % (self.emplid, self.unit.slug, self.last_program, self.admit_term))

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
                raise ValueError("Grad Student %s (%i) has programs in multiple units: that shouldn't be." % (gs.slug, gs.id))
        self.gradstudent = gs

    def get_student_info(self):
        student_info = {
            'student': self.gradstudent,
            'career': self,
            'statuses': list(GradStatus.objects.filter(student=self.gradstudent, hidden=False)
                .select_related('start').order_by('start__name', 'start_date')),
            'programs': list(GradProgramHistory.objects.filter(student=self.gradstudent)
                .select_related('start_semester', 'program').order_by('start_semester__name', 'starting')),
            'committee': list(Supervisor.objects.filter(student=self.gradstudent, removed=False) \
                .exclude(supervisor_type='POT')),
            'real_admit_term': self.admit_term,
        }
        return student_info

    def update_local_data(self, verbosity, dry_run):
        """
        Update local data for the GradStudent using what we found in SIMS
        """
        # make sure we can find it easily next time
        self.gradstudent.config[SIMS_SOURCE] = self.import_key()
        if self.adm_appl_nbr:
            self.gradstudent.config['adm_appl_nbr'] = self.adm_appl_nbr

        if self.metadata:
            self.metadata.update_local_data(self.gradstudent, verbosity=verbosity, dry_run=dry_run)

        student_info = self.get_student_info()
        self.student_info = student_info

        for h in self.happenings:
            # do this first for everything so a second pass can try harder to find things not matching in the first pass
            h.find_local_data(student_info, verbosity=verbosity)

        for h in self.happenings:
            h.update_local_data(student_info, verbosity=verbosity, dry_run=dry_run)

        # research area: let anything manually entered/changed win.
        if self.research_areas and not self.gradstudent.research_area:
            r = ' | '.join(self.research_areas)
            self.gradstudent.research_area = r + ' (from application)'
            if verbosity > 1:
                print("* Setting research area for %s/%s." % (self.emplid, self.unit.slug))

        # are there any GradProgramHistory objects happening before the student actually started (because they
        # deferred)? If so, defer them too.
        premature_gph = GradProgramHistory.objects.filter(student=self.gradstudent,
                                                          start_semester__name__lt=self.admit_term)
        for gph in premature_gph:
            gph.start_semester = STRM_MAP[self.admit_term]
            if verbosity:
                print("Deferring program start for %s/%s to %s." % (self.emplid, self.unit.slug, self.admit_term))
            if not dry_run:
                gph.save()

        # TODO: should we set GradStudent.config['start_semester'] here and be done with it?

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
        # if self.unit.slug == 'cmpt':
        #     # doesn't make sense for CMPT, since we're not importing everything else
        #     return

        if verbosity:
            for s in extra_statuses:
                print("Rogue grad status: %s was %s in %s" % (self.emplid, SHORT_STATUSES[s.status], s.start.name))
            for p in extra_programs:
                print("Rogue program change: %s in %s as of %s." % (self.emplid, p.program.slug, p.start_semester.name))
            for c in extra_committee:
                print("Rogue committee member: %s is a %s for %s" % (c.sortname(), SUPERVISOR_TYPE[c.supervisor_type], self.emplid))

