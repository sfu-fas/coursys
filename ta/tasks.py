from courselib.celerytasks import task
from celery.schedules import crontab
from ta.models import TAEvaluation
from coredata.models import Semester, SemesterWeek
import datetime

@task()
def check_and_execute_reminders():
    semester = Semester.current()
    
    # check every day - if it is Day 0, 7, 14, 28 of the semester

    today = datetime.date.today()

    # Day 0 - Release TA Evals for previous term
    # Day 0 - Send reminders for draft TA Evals to instructors for previous term
    if today == semester.start:
        TAEvaluation.send_reminders_for_draft_evals()
        TAEvaluation.release_ta_evals()

    # Day 7 - Send reminders for incomplete TA Evals for previous term
    if today == semester.start + datetime.timedelta(days=7):
        TAEvaluation.send_reminders_for_incomplete_evals()

    # Day 14 - Send reminders for incomplete TA Evals for previous term
    if today == semester.start + datetime.timedelta(days=14):
        TAEvaluation.send_reminders_for_incomplete_evals()

    # Day 28 - Send incomplete TA Evals to Admin for previous term
    if today == semester.start + datetime.timedelta(days=28):   
        TAEvaluation.send_incomplete_to_admin()