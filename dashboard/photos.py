from django.core.cache import cache
from django.conf import settings
from django.db import transaction
from coredata.models import Unit
from cache_utils.decorators import cached
import itertools, os
import hashlib, string, datetime, io
import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, json, base64
import celery
try:
    from PIL import Image
except ImportError:
    Image = None

import logging
logger = logging.getLogger('photo-backend')

ACCOUNT_NAME = 'cs'

URL_BASE = 'https://photos-api.its.sfu.ca/'
TOKEN_URL = URL_BASE + 'Account/Token'
PHOTO_URL = URL_BASE + 'Values/%s?includePhoto=true'
PASSWORD_URL = URL_BASE + 'Account/ChangePassword'
DUMMY_IMAGE_FILE = os.path.join(settings.BASE_DIR, 'media', 'images', 'No_image.JPG') # from http://commons.wikimedia.org/wiki/File:No_image.JPG

CHUNK_SIZE = 10 # max number of photos to fetch in one request
# max number of concurrent requests is managed by the celery 'photos' queue (it should be <= 5)

PHOTO_TIMEOUT = 20 # number of seconds the views will wait for the photo service
MAX_PHOTO_SIZE = 360 # max (width and height) dimensions of an image we'll return
TASK_BACKOFF = [1,2,3,4,5,6] # times to wait for photo fetching tasks


# from http://docs.python.org/2/library/itertools.html
def _grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itertools.zip_longest(fillvalue=fillvalue, *args)

def _photo_cache_key(emplid):
    return 'photo-image-'+str(emplid)
def _task_cache_key(emplid):
    return 'photo-task-'+str(emplid)

# functions that should actually be called to do stuff

def photo_for_view(emplid):
    """
    Get the photo, as needed by the view: check for cached JPEG, then cached task, else just fetch.

    Returns photos data, HTTP status.
    """
    from dashboard.tasks import fetch_photos_task
    task_key = _task_cache_key(emplid)
    image_key = _photo_cache_key(emplid)
    task_id = cache.get(task_key, None)
    photo_data = cache.get(image_key, None)
    data = None
    status = 200

    if photo_data:
        # found image in cache: was fetched previously or task completed before we got here
        logger.debug('cached data for %s' % (emplid))
        data = photo_data

    elif task_id and settings.USE_CELERY:
        # found a task fetching the photo: wait for it to complete and get the data
        from dashboard.tasks import fetch_photos_task
        task = fetch_photos_task.AsyncResult(task_id)
        logger.debug('task in cache for %s' % (emplid))
        for timeout in TASK_BACKOFF:
            # Rationale for this: these seems to be an occasional race condition, something like we find above that the
            # tasks exists but hasn't yet finished, but by the time we get here, it's done, so the task.get times out.
            # That leaves us waiting a long time for an image that ws actually in the cache by the time we looked. This
            # check-while-backing-off logic lets us find it fairly quickly, while still timing out reasonably on failure.
            try:
                task.get(timeout=timeout)
                data = cache.get(image_key, None)
            except celery.exceptions.TimeoutError:
                # see if we missed the task, but the result got to the cache
                data = cache.get(image_key, None)

            if data:
                break

    if not data and settings.USE_CELERY:
        # no cache warming, or didn't find: new task to get this photo
        logger.debug('no cache/task for %s' % (emplid))
        task = fetch_photos_task.apply(kwargs={'emplids': [emplid]})
        try:
            task.get(timeout=PHOTO_TIMEOUT)
        except celery.exceptions.TimeoutError:
            pass

        data = cache.get(image_key, None)

    if not data:
        # whatever happened above failed: use a no-photo placeholder
        logger.debug('using dummy image for %s' % (emplid))
        data = open(DUMMY_IMAGE_FILE, 'r').read()
        data = possibly_resize(data)
        status = 404

    return data, status


def pre_fetch_photos(emplids):
    """
    Start the tasks to fetch photos for the list of emplids.
    Returns a dictionary of emplid -> celery task_id that is getting that photo.
    """
    # break the collection of emplids into right-sized chunks
    if not settings.USE_CELERY:
        return

    from dashboard.tasks import fetch_photos_task
    task_map = {}
    # ignore emplids where we already have a cached image
    # (It's possible that the cache expires between this and actual photo use, but I'll take that chance.)
    emplids = [e for e in emplids if _photo_cache_key(e) not in cache]

    for group in _grouper(emplids, CHUNK_SIZE):
        # filter out the Nones introduced by grouper
        group = [str(e) for e in group if e is not None]
        t = fetch_photos_task.delay(emplids=group)

        # record which task is fetching which photos
        if t is not None: # returns None if no Celery available in devel environment: ignore the results then
            new_map = dict(zip(group, itertools.repeat(t.task_id, CHUNK_SIZE)))
            task_map.update(new_map)

    for emplid, task_id in task_map.items():
        cache.set(_task_cache_key(emplid), task_id, 60)



def do_photo_fetch(emplids):
    """
    Do the actual work of fetching photos: called by the celery task. Store them in the cache for finding by the view.
    """
    photos = _get_photos(emplids)
    for emplid in photos:
        cache.set(_photo_cache_key(emplid), photos[emplid], 3600*24*7)

    missing = set(emplids) - set(photos.keys())
    if missing:
        # some images missing: cache the failure, but not for as long
        data = open(DUMMY_IMAGE_FILE, 'rb').read()
        for emplid in missing:
            cache.set(_photo_cache_key(emplid), data, 3600)

    result = list(set(photos.keys()))
    logger.debug("do_photo_fetch(%r) returning %r" % (emplids, result))
    return result



# functions that actually get photos

@cached(45) # tokens should last for 60 seconds
def _get_photo_token():
    """
    Get auth token from photo service
    """
    token_data = urllib.parse.urlencode({'AccountName': ACCOUNT_NAME, 'Password': get_photo_password()})
    try:
        token_request = urllib.request.urlopen(TOKEN_URL, data=token_data)
    except IOError:
        return ''
    else:
        token_response = json.load(token_request)
        token = token_response['ServiceToken']
        return token

def possibly_resize(original):
    """
    Resize the jpeg to MAX_PHOTO_SIZE x MAX_PHOTO_SIZE if it's bigger. Otherwise, return as-is.
    """
    if Image is None:
        return original

    img = Image.open(io.StringIO(original))
    w,h = img.size
    if w <= MAX_PHOTO_SIZE and h <= MAX_PHOTO_SIZE:
        # original is reasonably-sized
        return original

    # resize
    img.thumbnail((MAX_PHOTO_SIZE, MAX_PHOTO_SIZE), Image.ANTIALIAS)

    resize = io.StringIO()
    img.save(resize, format='jpeg')
    return resize.getvalue()




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
    try:
        photo_request_obj = urllib.request.Request(url=photo_url, headers=headers)
        photo_request = urllib.request.urlopen(photo_request_obj, timeout=30)
    except IOError:
        return {}

    photo_response = json.load(photo_request)
    photos = {}
    for data in photo_response:
        if 'SfuId' not in data or 'PictureIdentification' not in data or not data['PictureIdentification']:
            continue
        key = data['SfuId']
        jpg = possibly_resize(base64.b64decode(data['PictureIdentification']))
        photos[key.strip()] = jpg
    return photos



# photo password management

LETTERS = string.ascii_letters
DIGITS = string.digits
PUNCTUATION = string.punctuation.replace('/', '')
ALL_CHARS = LETTERS + DIGITS + PUNCTUATION
PW_SERIES = '2'

def _choose_from(chars, seed):
    """
    Choose a character based on the seed: return new seed and the char.
    """
    l = len(chars)
    return (chars[seed%l], seed//l)

def generate_password(input_seed):
    """
    Generate some hard-to-guess but deterministic password.
    (deterministic so we have some hope of password recovery if something gets lost)

    Note: settings.SECRET_KEY is different (and actually secret) in production.
    """
    # generate seed integer
    secret = settings.SECRET_KEY
    seed_str = '_'.join([secret, input_seed, PW_SERIES, secret])
    h = hashlib.new('sha512')
    h.update(seed_str)
    seed = int(h.hexdigest(), 16)

    # use seed to pick characters: one letter, one digit, one punctuation, length 6-10
    letter, seed = _choose_from(LETTERS, seed)
    digit, seed = _choose_from(DIGITS, seed)
    punc, seed = _choose_from(PUNCTUATION, seed)
    pw = letter + digit + punc
    for i in range(7):
        c, seed = _choose_from(ALL_CHARS, seed)
        pw += c

    return pw


def get_photo_password():
    """
    Retrieve current photo service password.
    """
    # need to record the photo password somewhere in the DB so we can retrieve and update it as necessary.
    # This seems like the least-stupid place.
    u = Unit.objects.get(slug='univ')
    try:
        return u.config['photopass']
    except KeyError:
        return ''

def set_photo_password(p):
    """
    Set current photo service password.
    """
    u = Unit.objects.get(slug='univ')
    u.config['photopass'] = p
    u.save()

@transaction.atomic
def change_photo_password():
    """
    Change photo service password (passwords expire every 30 days, so must be automated).
    """
    if not settings.DO_IMPORTING_HERE:
        raise ValueError
    newpw = generate_password(datetime.date.today().isoformat())
    token_data = urllib.parse.urlencode({
        'AccountName': ACCOUNT_NAME,
        'OldPassword': get_photo_password(),
        'NewPassword': newpw,
    })
    resp = urllib.request.urlopen(PASSWORD_URL, data=token_data)
    resp_text = resp.read()
    set_photo_password(newpw)
    return resp_text
