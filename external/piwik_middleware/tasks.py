from celery.task import task
from importlib import import_module

from .conf import settings

@task(**settings.PIWIK_CELERY_TASK_KWARGS)
def track_page_view_task(kwargs):
    """
    Task to handle recording a request in Piwik asynchronously.
    """
    tracking_logic = import_module(settings.PIWIK_TRACKING_LOGIC).PiwikTrackerLogic()
    tracking_logic.do_track_page_view(**kwargs)