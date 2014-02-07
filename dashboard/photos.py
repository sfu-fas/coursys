from django.core.cache import cache
from django.conf import settings
from coredata.models import Unit
from cache_utils.decorators import cached
import itertools, os, time
import urllib, urllib2, json, base64

ACCOUNT_NAME = 'cs'
TOKEN_URL = 'https://at-dev.its.sfu.ca/photoservice/api/Account/Token'
PHOTO_URL = 'https://at-dev.its.sfu.ca/photoservice/api/Values/%s?includePhoto=true'
DUMMY_IMAGE_FILE = os.path.join(settings.STATIC_ROOT, 'images', 'No_image.JPG') # from http://commons.wikimedia.org/wiki/File:No_image.JPG
CHUNK_SIZE = 10 # max number of photos to fetch in one request
# max number of concurrent requests is managed by the celery 'photos' queue (it should be <= 5)
PHOTO_TIMEOUT = 10 # number of seconds the views will wait for the photo service



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
    # ignore emplids where we already have a cached image
    # (It's possible that the cache expires between this and actual photo use, but I'll take that chance.)
    emplids = [e for e in emplids if not cache.has_key('photo-image-'+unicode(e))]

    for group in _grouper(emplids, CHUNK_SIZE):
        # filter out the Nones introduced by grouper
        group = [unicode(e) for e in group if e is not None]
        t = fetch_photos_task.delay(emplids=group)

        # record which task is fetching which photos
        new_map = dict(itertools.izip(group, itertools.repeat(t.task_id, CHUNK_SIZE)))
        task_map.update(new_map)

    return task_map


def do_photo_fetch(emplids):
    """
    Do the actual work of fetching photos: called by the celery task. Store them in the cache for finding by the view.
    """
    photos = _get_photos(emplids)
    for emplid in photos:
        cache.set('photo-image-'+unicode(emplid), photos[emplid], 3600*24)

    missing = set(emplids) - set(photos.keys())
    if not missing:
        return

    # some images missing: cache the failure, but not for as long
    data = open(DUMMY_IMAGE_FILE, 'rb').read()
    for emplid in missing:
        cache.set('photo-image-'+unicode(emplid), data, 3600)



# functions that actually interact with the photo service

def get_photo_password():
    # need to record the photo password somewhere in the DB so we can retrieve and update it as necessary.
    # This seems like the least-stupid place.
    u = Unit.objects.get(slug='univ')
    return u.config['photopass']

def set_photo_password(p):
    u = Unit.objects.get(slug='univ')
    u.config['photopass'] = p
    u.save()


@cached(45) # tokens should last for 60 seconds
def _get_photo_token():
    """
    Get auth token from photo service
    """
    token_data = urllib.urlencode({'AccountName': ACCOUNT_NAME, 'Password': get_photo_password()})
    token_request = urllib2.urlopen(TOKEN_URL, data=token_data)
    token_response = json.load(token_request)
    token = token_response['ServiceToken']
    return token

def _get_photos(emplids):
    """
    Get actual photo data from photo service. Returns emplid -> JPEG data dict
    """
    if not emplids:
        return {}

    token = _get_photo_token()
    emplid_str = ','.join(str(e) for e in emplids)

    photo_url = PHOTO_URL % (emplid_str)
    headers = {'Authorization': 'Bearer ' + token}
    photo_request_obj = urllib2.Request(url=photo_url, headers=headers)
    photo_request = urllib2.urlopen(photo_request_obj)
    photo_response = json.load(photo_request)
    photos = {}
    for data in photo_response:
        if 'SFUID' not in data or 'STUDENT_PICTURE' not in data or not data['STUDENT_PICTURE']:
            continue
        key = data['SFUID']
        jpg = base64.b64decode(data['STUDENT_PICTURE'])
        photos[key] = jpg
    return photos



