from typing import List
from courselib.celerytasks import task
from grades.models import Activity
from submission.models.base import SimilarityResult
from submission.moss import run_moss, MOSSError


@task()
def run_moss_task(activity_id: int, activity_ids: List[int], language: str, result_id: int):
    activities = Activity.objects.filter(id__in=activity_ids)
    activity = Activity.objects.get(id=activity_id)
    result = SimilarityResult.objects.get(id=result_id)
    try:
        run_moss(activity, list(activities), language, result)
    except MOSSError as e:
        result.config['error'] = str(e)
        result.save()
