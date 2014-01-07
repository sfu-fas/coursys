from courselib.svn import update_repository
from celery.task import task

@task(rate_limit="30/m", max_retries=2)
def update_repository_task(*args, **kwargs):
    return update_repository(*args, **kwargs)



# some tasks for testing/experimenting
import time
from celery.task import periodic_task
from celery.task.schedules import crontab

@task(queue='fast')
def ping():
    return True

@task(rate_limit='60/m')
def slow_task():
    #time.sleep(5)
    print "HELLO SLOW TASK"
    return True

@periodic_task(run_every=crontab())
def test_periodic_task():
    print "HELLO PERIODIC TASK"
    return True

