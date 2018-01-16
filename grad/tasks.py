from courselib.celerytasks import periodic_task
from celery.schedules import crontab
from grad.models import GradStudent, GradStatus, GradProgramHistory
from coredata.models import Semester

@periodic_task(run_every=crontab(minute=0, hour=3))
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

