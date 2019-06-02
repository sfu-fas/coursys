from courselib.celerytasks import task, periodic_task
from celery.schedules import crontab
from coredata.queries import SIMSConn, PLAN_QUERY, SUBPLAN_QUERY
from advisornotes.models import AdvisorVisit
import datetime
from collections import defaultdict

@task(queue='sims')
def update_program_info(advisor_visit_ids):
    visits = AdvisorVisit.objects.filter(id__in=advisor_visit_ids) \
            .exclude(student__isnull=True).select_related('student')
    emplids = set(v.student.emplid for v in visits)

    # find plans and subplans for these students
    programs = defaultdict(list)
    db = SIMSConn()
    db.execute(PLAN_QUERY.substitute({'where': 'prog.emplid IN %s'}), (emplids,))
    for emplid, planid, _, _ in db:
        programs[emplid].append(planid)

    db.execute(SUBPLAN_QUERY.substitute({'where': 'prog.emplid IN %s'}), (emplids,))
    for emplid, planid, _, _ in db:
        programs[emplid].append(planid)

    # add them to the visits we're trying to update
    for v in visits:
        v.config['sims_programs'] = programs[str(v.student.emplid)]
        v.save()


@periodic_task(run_every=crontab(minute=0, hour='2'))
def program_info_for_advisorvisits():
    """
    Find any AdvisorVisits that need their sims_programs filled in; pass a task to do that off to the sims queue.
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(days=5)
    visit_ids = AdvisorVisit.objects.filter(created_at__gte=cutoff)\
            .exclude(config__contains='sims_programs').exclude(student__isnull=True) \
            .order_by().values_list('id', flat=True)
    visit_ids = list(visit_ids)

    if visit_ids:
        update_program_info.delay(visit_ids)