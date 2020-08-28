from coredata.models import CourseOffering
from marking.models import copy_setup_pages
from celery.task import task


@task(queue='fast')
def copy_setup_pages_task(copy_from_slug, copy_to_slug):
    """
    Call copy_setup_pages as a task (since it can be slow with many pages).
    """
    course_copy_from = CourseOffering.objects.get(slug=copy_from_slug)
    course_copy_to = CourseOffering.objects.get(slug=copy_to_slug)
    copy_setup_pages(course_copy_from, course_copy_to)