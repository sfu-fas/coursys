# prettification of celery tasks

from django.conf import settings
from celery.task import task

class DummyTask(object):
    "A Task-like object that fakes enough to use in a non-celery environment"
    def __init__(self, func):
        self.func = func

    def delay(self, *args, **kwargs):
        res = self.func(*args, **kwargs)
        return DummyResult(res)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    apply_async = delay
    apply = __call__

class DummyResult(object):
    "A task result-like object that fakes enough to use in a non-celery environment"
    def __init__(self, result):
        self.result = result

    def get(self):
        return self.result



def flexible_task(**kwargs):
    """
    A wrapper for @task that uses the dummy task/result classes if celery is not enabled.
    """
    if settings.USE_CELERY:
        def decorator(func):
            return task(**kwargs)(func)
    else:
        def decorator(func):
            return DummyTask(func)
    return decorator
