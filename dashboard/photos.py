from django.core.cache import cache
from django.conf import settings
import itertools, os, time

DUMMY_IMAGE_FILE = os.path.join(settings.STATIC_ROOT, 'images', 'default-photo.png')
CHUNK_SIZE = 10 # max number of photos to fetch in one request
# max number of concurrent requests is managed by the celery 'photos' queue (it should be <= 5)



# from http://docs.python.org/2/library/itertools.html
def _grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args)

def fetch_photos(emplids):
    """
    Start the tasks to fetch photos for the list of emplids.
    Returns a dictionary of emplid -> celery task_id that is getting that photo.
    """
    # break the collection of emplids into right-sized chunks
    from dashboard.tasks import fetch_photos_task
    task_map = {}
    for group in _grouper(emplids, CHUNK_SIZE):
        # filter out photos already in the cache (and the Nones introduced by grouper)
        # (It's possible that the cache expires between this and actual photo use, but I'll take that chance.)
        group = [e for e in group if e is not None and not cache.has_key('photo-image-'+unicode(e)) ]

        t = fetch_photos_task.delay(emplids=group)

        # record which task is fetching which photos
        new_map = dict(itertools.izip(group, itertools.repeat(t.task_id, CHUNK_SIZE)))
        task_map.update(new_map)

    return task_map


def do_photo_fetch(emplids):
    """
    Do the actual work of fetching photos: called by the celery task.
    """
    # dummy behaviour until we can do better
    data = open(DUMMY_IMAGE_FILE, 'r').read()
    time.sleep(2)

    for emplid in emplids:
        cache.set('photo-image-'+unicode(emplid), data, 3600*24)

    return data
