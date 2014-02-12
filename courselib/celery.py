# prettification of celery tasks

from django.conf import settings
from celery.task import task

def flexible_task(**kwargs):
    if settings.USE_CELERY:
        def decorator(func):
            return task(**kwargs)(func).delay
    else:
        def decorator(func):
            return func
    return decorator
