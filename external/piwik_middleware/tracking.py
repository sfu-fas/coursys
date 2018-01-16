from piwikapi.tracking import PiwikTracker
from piwikapi.tests.request import FakeRequest
from ipware.ip import get_real_ip
from socket import error as SocketError
import urllib.request, urllib.error, urllib.parse
import time, datetime, pytz
import hashlib

from .conf import settings

SESSION_COOKIE_NAME = settings.SESSION_COOKIE_NAME

PIWIK_SITEID = settings.PIWIK_SITEID
PIWIK_URL = settings.PIWIK_URL
PIWIK_TOKEN = settings.PIWIK_TOKEN
PIWIK_FAIL_SILENTLY = settings.PIWIK_FAIL_SILENTLY
PIWIK_FORCE_HOST = settings.PIWIK_FORCE_HOST

try:
    from .tasks import track_page_view_task
except ValueError:
    # if we don't have the celery module around, the import will fail
    track_page_view_task = None

USE_CELERY = track_page_view_task and settings.PIWIK_CELERY

# errors that might be thrown by the API call that variously mean "bad network thing".
urllib_errors = (urllib.error.URLError, urllib.error.HTTPError, SocketError, IOError)


class PiwikTrackerLogic(object):
    """
    Logic associated with recording hits to Piwik.

    This module is referenced by settings.PIWIK_TRACKING_LOGIC and can be overridden/subclassed to modify behaviour.
    """
    def get_track_kwargs(self, request, response=None):
        """
        Get kwargs that can be passed to the TRACKING_FUNCTION (track_page_view by default).

        Return value must be JSON serializable if settings.PIWIK_USE_CELERY.
        """
        # copy the META members that might actually be HTTP headers
        headers = dict(
            (k, v.decode('cp1250')) # There have been some wacky bytes in headers. Make sure they can be JSON serialized
            for k,v in request.META.items()
            if isinstance(k, str) and isinstance(v, str)
        )
        headers['HTTPS'] = request.is_secure()

        userid = request.user.username if hasattr(request, 'user') and request.user.is_authenticated() else None

        kwargs = {
            'headers': headers,
            'title': None,
            'userid': userid,
            'reqtime': time.time(),
            #'session_key': request.COOKIES.get(SESSION_COOKIE_NAME, None),
            'status_code': response.status_code if response else None,
        }
        return kwargs

    def do_track_page_view(self, headers, reqtime=None, title=None, userid=None, session_key=None, status_code=None,
                fail_silently=PIWIK_FAIL_SILENTLY):
        """
        Actually record the page view with Piwik: do the actual work with kwargs from self.get_track_kwargs
        """
        request = FakeRequest(headers)
        pt = PiwikTracker(PIWIK_SITEID, request)

        pt.set_api_url(PIWIK_URL)
        pt.set_token_auth(PIWIK_TOKEN)

        pt.set_ip(get_real_ip(request))

        if session_key:
            visitor_id = hashlib.sha512(session_key).hexdigest()[0:PiwikTracker.LENGTH_VISITOR_ID]
            pt.set_visitor_id(visitor_id)

        if reqtime:
            dt = datetime.datetime.fromtimestamp(reqtime, pytz.utc)
            pt.set_force_visit_date_time(dt)

        if userid:
            pt.set_custom_variable(1, 'userid', userid, scope='visit')

        if status_code:
            pt.set_custom_variable(2, 'status_code', status_code, scope='page')

        if PIWIK_FORCE_HOST:
            pt._set_host(PIWIK_FORCE_HOST)

        try:
            pt.do_track_page_view(title)
        except urllib_errors:
            if not fail_silently:
                raise

    def track_page_view(self, request, response=None):
        """
        Record a page view in Piwik.
        """
        if not PIWIK_URL or not PIWIK_TOKEN:
            # URL and TOKEN must be set to get us anywhere
            return

        kwargs = self.get_track_kwargs(request, response)
        if USE_CELERY:
            track_page_view_task.delay(kwargs)
        else:
            self.do_track_page_view(**kwargs)
