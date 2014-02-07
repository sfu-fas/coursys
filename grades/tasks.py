from django.conf import settings
from dashboard.models import NewsItem
from grades.models import Activity, NumericGrade, LetterGrade, GradeHistory
import itertools

try:
    from celery.task import task
except ImportError:
    def task(*args, **kwargs):
        def decorator(*args, **kwargs):
            return None
        return decorator

def _send_grade_released_news(activity_id):
    activity = Activity.objects.get(id=activity_id)
    NewsItem.for_members(member_kwargs={'offering': activity.offering},
                newsitem_kwargs={
                    'author': None, 'course': activity.offering, 'source_app': 'grades',
                    'title': "%s grade released" % (activity.name),
                    'content': 'Grades have been released for %s in %s.'
                      % (activity.name, activity.offering.name()),
                    'url': activity.get_absolute_url()})

@task(max_retries=2)
def send_grade_released_news_task(activity_id):
    _send_grade_released_news(activity_id)



def _create_grade_released_history(activity_id, entered_by_id):
    num_grades = NumericGrade.objects.filter(id=activity_id)
    let_grades = LetterGrade.objects.filter(id=activity_id)
    activity = Activity.objects.get(id=activity_id)
    for g in itertools.chain(num_grades, let_grades):
        gh = GradeHistory(activity_id=activity, member=g.member, entered_by_id=entered_by_id, activity_status=activity.status,
                          grade_flag=g.flag, comment=g.comment, mark=None, group=None, status_change=True)
        if hasattr(g, 'value'):
            # NumericGrade
            gh.numeric_grade = g.value
        else:
            # LetterGrade
            gh.letter_grade = g.letter_grade
        
        gh.save()

@task(queue='fast')
def create_grade_released_history_task(activity_id, entered_by_id):
    _create_grade_released_history(activity_id, entered_by_id)


# let these work with or without Celery
if settings.USE_CELERY:
    send_grade_released_news = send_grade_released_news_task.delay
    create_grade_released_history = create_grade_released_history_task.delay
else:
    send_grade_released_news = _send_grade_released_news
    create_grade_released_history = _create_grade_released_history
