from courselib.svn import update_repository as _update_repository
from celery.task import task

@task(rate_limit="30/m", max_retries=2)
def update_repository(*args, **kwargs):
    return _update_repository(*args, **kwargs)

@task
def ping():
    return True
