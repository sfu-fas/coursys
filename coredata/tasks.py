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








# daily import tasks

from coredata.models import CourseOffering
from coredata.importer import import_offerings, import_offering_members, update_amaint_userids, fix_emplid
from celery import chain
import logging
logger = logging.getLogger('coredata.importer')

@task(queue='sims')
def daily_import():
    """
    Enter all of the daily import tasks into the queue, where they can grind away from there.

    The import is broken up into tasks for a few reasons: it can be paused by stopping the sims queue if necssary;
    works around the celery task time limit.
    """
    tasks = [
        get_amaint_userids.si(),
        fix_unknown_emplids.si(),
        get_import_offerings_task(),
    ]

    chain(*tasks).apply_async()


@task(queue='sims')
def get_amaint_userids():
    logger.info('Updating userids from AMAINT')
    #update_amaint_userids()

@task(queue='sims')
def fix_unknown_emplids():
    logger.info('Fixing unknown emplids')
    #fix_emplid()

def get_import_offerings_task():
    """
    Doesn't actually call the jobs: just returns a celery task to be called.
    """
    offerings = import_offerings(extra_where="ct.subject='CMPT' and ct.catalog_nbr IN (' 383', ' 470')")
    #offerings = import_offerings(cancel_missing=True)
    offerings = list(offerings)
    offerings.sort()

    offering_import_chain = chain(*[import_one_offering.si(o.slug) for o in offerings]) # could be a group?
    return offering_import_chain


@task(queue='sims')
def import_one_offering(offering_slug):
    logger.debug('Importing %s' % (offering_slug,))
    offering = CourseOffering.objects.get(slug=offering_slug)
    #import_offering_members(offering)

