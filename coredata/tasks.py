from courselib.svn import update_repository
from coredata.management.commands import backup_db
from celery.task import task


@task(rate_limit="30/m", max_retries=2)
def update_repository_task(*args, **kwargs):
    return update_repository(*args, **kwargs)



# some tasks for testing/experimenting
import time
from celery.task import periodic_task
from celery.schedules import crontab

@task(queue='fast')
def ping():
    return True

@task(rate_limit='60/m')
def slow_task():
    #time.sleep(5)
    print "HELLO SLOW TASK"
    return True

#@periodic_task(run_every=crontab())
#def test_periodic_task():
#    print "HELLO PERIODIC TASK"
#    return True


@periodic_task(run_every=crontab(minute=0, hour='*/3'))
def backup_database():
    backup_db.Command().handle(clean_old=True)