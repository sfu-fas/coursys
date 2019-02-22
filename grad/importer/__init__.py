"""
All of the logic to handle import GradStudents (and GradProgramHistory, GradStatus, Supervisor) from SIMS into CourSys.

The basic idea:
 1. Everything is brought in with various SIMS queries.
 2. This is used to construct various objects that represent "happenings": status changes, program changes, committee
    members.
 3. Happenings are chopped up into "careers" that represent a unique application+unit. These correspond to GradStudent
    objects.
 4. All of the happenings know how to update themselves in CourSys: finding old versions of that fact if available and
    creating/updating as necessary.

All of this is surprisingly intricate, particularly 3. Did you know you can the same program three times concurrently,
or form a grad committee before you transfer into program (but after you applied for it but abandoned the application)?
Turns out you can, and a thousand other things.

Part 4 is tricky because we want staff to be able to enter facts before they hit SIMS (sometimes there's a long lag,
and they need them in-place before the paperwork makes it), and then confirm/polish once it's in SIMS. A lot of the
logic around this is trying to find the similar-enough fact that was manually entered and claiming it.
"""

from .parameters import IMPORT_UNIT_SLUGS
from .queries import grad_program_changes, grad_appl_program_changes, grad_semesters, committee_members, \
    grad_metadata, research_areas, metadata_translation_tables
from .happenings import build_program_map, ProgramStatusChange, ApplProgramChange, GradSemester, CommitteeMembership, \
    GradMetadata, GradResearchArea
from .timeline import GradTimeline

from django.db import transaction
from coredata.models import Unit
import itertools
from collections import defaultdict

# TODO: some Supervisors were imported from cortez as external with "userid@sfu.ca". Ferret them out
# TODO: adjust LEAV statuses depending on the NWD/WRD status from ps_stdnt_car_term?
# TODO: CMPT distinction between thesis/project/course in SIMS?
# TODO: if transferred to another unit, copy the application/matriculation events over for better program history?
# TODO: could set the CMPT DDP flag for relevant programs


def manual_cleanups(dry_run, verbosity):
    """
    These are cleanups of old data that make the real import work well and leave less junk to clean later.
    """
    if dry_run:
        return
    pass


def _batch_call(func, args, batchsize=500):
    """
    Call func(args), but breaking up args into manageable chunks.
    """
    for i in range(0, len(args), batchsize):
        batch = args[i:i+batchsize]
        yield func(batch)


def check_environment():
    """
    Check our world to make sure things are sane.
    """
    from coredata.models import VISA_STATUSES
    _, _, visas = metadata_translation_tables()
    const = set(dict(VISA_STATUSES).keys())
    sims = set([v for _,v in list(visas.values())])
    assert const == sims, "coredata.models.VISA_STATUSES doesn't match the possible visa values from SIMS"


def get_timelines(verbosity, import_emplids=None):
    """
    Get all timeline data for programs we care about.
    """
    prog_map = build_program_map()
    import_units = Unit.objects.filter(slug__in=IMPORT_UNIT_SLUGS)
    acad_progs = [acad_prog for acad_prog, program in prog_map.items() if program.unit in import_units]

    check_environment()

    # always do these: safe and rest of the import gets weird without them.
    manual_cleanups(verbosity=verbosity, dry_run=False)

    # Get the basic program data we need to generate a Timeline object (JSONable so we can throw it in celery later)
    # each entry is a tuple of ('ClassName', *init_args)
    timeline_data = defaultdict(list)
    if import_emplids:
        import_emplids = set(import_emplids)
    for acad_prog in acad_progs:
        prog_changes = grad_program_changes(acad_prog)
        for p in prog_changes:
            emplid = p[1]
            if import_emplids and emplid not in import_emplids:
                continue
            d = timeline_data[emplid]
            d.append(p)

        # temporarily disable while we settle out everything else
        appl_changes = grad_appl_program_changes(acad_prog)
        for a in appl_changes:
            emplid = a[1]
            if import_emplids and emplid not in import_emplids:
                continue
            d = timeline_data[emplid]
            d.append(a)

    timeline_data = dict(timeline_data)

    if import_emplids:
        emplids = list(import_emplids)
    else:
        emplids = sorted(timeline_data.keys())

    # fetch all of the grad/committee data now that we know who to fetch for
    for r in itertools.chain(*_batch_call(grad_semesters, emplids)):
        emplid = r[1]
        timeline_data[emplid].append(r)
    for r in itertools.chain(*_batch_call(committee_members, emplids)):
        emplid = r[1]
        timeline_data[emplid].append(r)
    for r in itertools.chain(*_batch_call(grad_metadata, emplids, batchsize=50)):
        emplid = r[1]
        timeline_data[emplid].append(r)
    for r in itertools.chain(*_batch_call(research_areas, emplids)):
        emplid = r[1]
        timeline_data[emplid].append(r)

    return timeline_data


def build_timeline(emplid, data):
    timeline = GradTimeline(emplid)
    for d in data:
        if d[0] == 'ProgramStatusChange':
            h = ProgramStatusChange(*(d[1:]))
        elif d[0] == 'ApplProgramChange':
            h = ApplProgramChange(*(d[1:]))
        elif d[0] == 'GradSemester':
            h = GradSemester(*(d[1:]))
        elif d[0] == 'CommitteeMembership':
            h = CommitteeMembership(*(d[1:]))
        elif d[0] == 'GradMetadata':
            h = GradMetadata(*(d[1:]))
        elif d[0] == 'GradResearchArea':
            h = GradResearchArea(*(d[1:]))
        else:
            raise ValueError(d[0])

        timeline.add(h)

    return timeline

def import_timeline(timeline, dry_run, verbosity):
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


def import_timelines(timeline_data, dry_run, verbosity):
    """
    Process the timeline data into our database.
    """
    for emplid, data in timeline_data.items():
        timeline = build_timeline(emplid, data)
        import_timeline(timeline, dry_run=dry_run, verbosity=verbosity)


def import_grads(dry_run, verbosity, import_emplids=None):
    timeline_data = get_timelines(verbosity=verbosity, import_emplids=import_emplids)
    # note: it would be perfectly fine to break up timeline_data into smaller chunks and run import_timelines as subtasks
    import_timelines(timeline_data, dry_run=dry_run, verbosity=verbosity)

