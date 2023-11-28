# prettification of celery tasks
import datetime

from django.conf import settings
from celery import shared_task

from django.core.mail import mail_admins
from functools import wraps
import sys, traceback

from log.models import CeleryTaskLog


def task(*d_args, **d_kwargs):
    # behaves like @task, but emails about exceptions.
    def real_decorator(f):
        @shared_task(*d_args, **d_kwargs)
        @wraps(f)
        def wrapper(*f_args, **f_kwargs):
            # try the task; email any exceptions we get
            log_data = {
                'queue': getattr(wrapper, 'queue', None),
            }
            start = datetime.datetime.now()
            try:
                res = f(*f_args, **f_kwargs)
            except Exception as e:
                # email admins and re-raise
                exc_type, exc_value, exc_traceback = sys.exc_info()
                subject = 'task failure in %s.%s' % (f.__module__, f.__name__)
                msg = 'The task %s.%s failed:\n\n%s' % (f.__module__, f.__name__,
                        '\n'.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                mail_admins(subject=subject, message=msg, fail_silently=True)
                log_data['exception'] = e.__class__.__name__
                log_data['exception_message'] = str(e)
                raise
            finally:
                # log the task
                end = datetime.datetime.now()
                task = f'{f.__module__}.{f.__name__}'

                log = CeleryTaskLog(time=start, duration=end - start, task=task, data=log_data)
                log.save()

            return res
        return wrapper
    return real_decorator


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
