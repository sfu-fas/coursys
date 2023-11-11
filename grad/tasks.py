import datetime, itertools
from coredata.models import Semester
from courselib.celerytasks import task
from grad.models import GradStatus, GradProgramHistory, GradStudent, STATUS_ACTIVE, STATUS_APPLICANT
from grad import importer as grad_importer
from coredata.tasks import grouper
import celery
from django.conf import settings


@task()
def grad_daily_import():
    """
    Enter the daily grad student-related import tasks into the queue.
    """
    if not settings.DO_IMPORTING_HERE:
        return

    import_grad_task_chain().apply_async(serializer='pickle')
    get_update_grads_task().apply_async()


@task()
def update_statuses_to_current():
    """
    Update the denormalized grad status fields to reflect the current time (and catch statuses that were entered in the
    future).

    Doesn't really need to be run daily, but that's easier than catching the missed celery run on the first day of class.
    """
    this_sem = Semester.current()

    # grads who have a status or program that starts this semester
    status_student_ids = GradStatus.objects.filter(start=this_sem).order_by().values_list('student_id', flat=True)
    program_student_ids = GradProgramHistory.objects.filter(start_semester=this_sem).order_by().values_list('student_id', flat=True)
    student_ids = set(status_student_ids) | set(program_student_ids)

    students = set(GradStudent.objects.filter(id__in=student_ids).distinct())

    # make sure it is actually in the status fields
    for gs in students:
        gs.update_status_fields()


def import_grad_task_chain(start=False):
    """
    Create a chain of tasks for import of grad timelines.
    """
    timeline_data = grad_importer.get_timelines(verbosity=0, import_emplids=None)
    timeline_groups = grouper(timeline_data.items(), 50)
    grad_import_chain = celery.chain(*[import_timelines.si(dict(td)) for td in timeline_groups])
    if start:
        grad_import_chain.apply_async(serializer='pickle')
    return grad_import_chain


# must be serialized with pickle because there are datetime objects in the arguments
@task(queue='sims', serializer='pickle')
def import_timelines(timeline_data: dict) -> None:
    """
    Task to call import_timelines on a reasonably-sized of grads.
    """
    assert len(timeline_data) < 500  # the whole point is to keep tasks reasonably short.
    grad_importer.import_timelines(timeline_data, dry_run=False, verbosity=0)


def get_update_grads_task():
    """
    Get grad students to import, and build tasks (in groups) to do the work.

    Doesn't actually call the jobs: just returns a celery task to be called.
    """
    active = GradStudent.objects.filter(current_status__in=STATUS_ACTIVE).select_related('person')
    applicants = GradStudent.objects.filter(current_status__in=STATUS_APPLICANT,
                 updated_at__gt=datetime.datetime.now()-datetime.timedelta(days=7)).select_related('person')
    grads = itertools.chain(active, applicants)
    emplids = set(gs.person.emplid for gs in grads)
    emplid_groups = grouper(emplids, 20)

    grad_import_chain = celery.chain(*[import_grad_group.si(list(emplids)) for emplids in emplid_groups])
    return grad_import_chain


@task(queue='sims')
def import_grad_group(emplids):
    """
    Import grad Person information for this collection of emplids.
    """
    from coredata.importer import get_person_grad
    for emplid in emplids:
        get_person_grad(emplid)
