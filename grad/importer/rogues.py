from .parameters import SIMS_SOURCE
from grad.models import GradStudent, CompletedRequirement, Letter, Scholarship, OtherFunding, Promise, FinancialComment
from grad.models import GradFlagValue, ProgressReport, ExternalDocument, GradProgramHistory, GradStatus, Supervisor

# TODO: purge any GradStatus before a few semesters ago that isn't confirmed?

def manual_cleanups(dry_run, verbosity):
    """
    These are cleanups of old data that make the real import work well and leave less junk to clean later.
    """
    if dry_run:
        return
    pass


def find_true_home(obj, dry_run):
    """
    Find the true GradStudent where this object (on a rogue GradStudents) belongs.
    """
    old_gs = obj.student
    new_gss = list(GradStudent.objects.filter(person=old_gs.person, program=old_gs.program, config__contains=SIMS_SOURCE))
    if len(new_gss) > 2:
        raise ValueError("Multiple matches for %s %s: please fix manually" % (old_gs.slug, obj.__class__.__name__))
    elif len(new_gss) == 0:
        raise ValueError("No match for %s %s: please fix manually" % (old_gs.slug, obj.__class__.__name__))

    new_gs = new_gss[0]
    obj.student = new_gs
    if not dry_run:
        obj.save()

def rogue_gradstudents(unit_slug, dry_run, verbosity):
    """
    Examine grad students in this unit. Identify rogues that could be deleted.
    """
    # other things that could be found and possibly purged:
    # GradProgramHistory that's unconfirmed and to the program they're *already in*
    # GradStatus on-leave that's unconfirmed and in-the-past-enough that it's not a recent manual entry
    # There are Supervisors with external=='-None-' for CMPT: those can go.
    manual_cleanups(verbosity=verbosity, dry_run=False)

    gss = GradStudent.objects.filter(program__unit__slug=unit_slug, start_semester__name__gte='1051')

    # what GradStudents haven't been found in SIMS?
    gs_unco = [gs for gs in gss if SIMS_SOURCE not in gs.config]

    # do the unconfirmed ones have any confirmed data associated? (implicitly ignoring manually-entered data on these fields)
    for GradModel in [GradProgramHistory, GradStatus, Supervisor]:
        res = [s.student.slug for s in GradModel.objects.filter(student__in=gs_unco) if SIMS_SOURCE in s.config]
        if res:
            raise ValueError('Found an unconfirmed %s for %s, who is rogue.' % (GradModel.__name__, s.student.slug))

    # do they have any other data entered manually?
    for GradModel in [CompletedRequirement, Letter, Scholarship, OtherFunding, Promise, FinancialComment, GradFlagValue, ProgressReport, ExternalDocument]:
        res = GradModel.objects.filter(student__in=gs_unco)
        #if res:
        #   raise ValueError, 'Found a %s for %s, who is rogue.' % (GradModel.__name__, s.student.slug)
        for r in res:
            find_true_home(r, dry_run=dry_run)

    for gs in gs_unco:
        if verbosity:
            print("Soft-deleting %s." % (gs.slug))
        if not dry_run:
            gs.current_status = 'DELE'
            gs.save()

def rogue_leaves(unit_slug, dry_run, verbosity):
    """
    On-leave events that were introduced by the old importer, likely in error
    """
    # TODO: removing these leaves many students with adjacent redundant ACTI statuses: clean those too
    statuses = GradStatus.objects \
            .filter(status='LEAV', student__program__unit__slug=unit_slug) \
            .filter(student__config__contains=SIMS_SOURCE) \
            .exclude(config__contains=SIMS_SOURCE) \
            .select_related('student')

    if not dry_run:
        statuses.update(hidden=True)

    students = sorted(list(set([s.student for s in statuses])), key=lambda s: s.slug)
    for gs in students:
        if verbosity:
            print("Removing on-leave status(es) for %s." % (gs.slug))

        if not dry_run:
            gs.update_status_fields()



def rogue_grad_finder(unit_slug, dry_run=False, verbosity=1):
    #rogue_gradstudents(unit_slug, dry_run=dry_run, verbosity=verbosity)
    rogue_leaves(unit_slug, dry_run=dry_run, verbosity=verbosity)

