from courselib.svn import update_repository
from celery.task import task

@task(rate_limit="30/m", max_retries=2, priority=9)
def update_repository_task(*args, **kwargs):
    return update_repository(*args, **kwargs)

@task(priority=2)
def ping():
    return True
