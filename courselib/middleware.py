import time
import logging
from django.db import connection
from django.conf import settings
logger = logging.getLogger(__name__)

class MonitoringMiddleware(object):
    """
    Middleware to log requests that take strangely long.
    """
    def process_request(self, request):
        request.monitoring_starttime = time.time()

    def process_response(self, request, response):
        # see if things took too long, and log if they did
        if hasattr(request, 'monitoring_starttime'):
            duration = time.time() - request.monitoring_starttime
            if duration > getattr(settings, 'SLOW_THRESHOLD', 5):
                if not (request.path.startswith('/login/?next=')): # ignore requests we can't do anything about
                    logger.info('%0.1fs to return %s %s?%s' % (duration, request.method, request.path, request.META['QUERY_STRING']))
                    for q in connection.queries:
                        logger.debug('%s\t%s' % (q['sql'], q['time']))

        return response



import sys
from courselib.auth import HttpError
try:
    from MySQLdb import OperationalError
except ImportError:
    OperationalError = None

class ExceptionIgnorer(object):
    """
    Middleware to eat the exception that we really don't need to see.
    """
    def process_exception(self, request, exception):
        import traceback
        exc_info = sys.exc_info()
        format = traceback.format_exc(exc_info[2])
        message = unicode(exception)
        if (isinstance(exception, IOError) and '_verify(ticket, service)' in format
            and ('Connection reset by peer' in message
                 or 'Name or service not known' in message
                 or 'Connection timed out' in message
                 or 'EOF occurred in violation of protocol' in message)):
            # CAS verification timeout
            return HttpError(request, status=500, title="CAS Error", error="Could not contact the CAS server to verify your credentials. Please try logging in again.")
        elif isinstance(exception, AssertionError) and "Django CAS middleware requires authentication middleware" in format:
            # CAS choke
            return HttpError(request, status=500, title="CAS Error", error="Could not contact the CAS server to verify your credentials. Please try logging in again.")
        elif isinstance(exception, EOFError) and "return request.POST.get('csrfmiddlewaretoken', '')" in format:
            # file upload EOF
            return HttpError(request, status=500, title="Upload Error", error="Upload seems to have not completed properly.")
        elif OperationalError is not None and isinstance(exception, OperationalError) and "Lost connection to MySQL server at 'reading initial communication packet'" in format:
            # lost main DB
            return HttpError(request, status=500, title="Database Error", error="Unable to connect to database.")
        elif OperationalError is not None and isinstance(exception, OperationalError) and "MySQL server has gone away" in format:
            # lost main DB
            return HttpError(request, status=500, title="Database Error", error="Unable to connect to database.")
        elif isinstance(exception, AssertionError) and "The Django CAS middleware requires authentication middleware" in format:
            # wacky authentication thing that means the database is missing, or something
            return HttpError(request, status=500, title="Database Error", error="Unable to connect to database.")



from piwikapi.tracking import PiwikTracker
from piwikapi.tests.request import FakeRequest
from ipware.ip import get_real_ip
import hashlib
PIWIK_URL = settings.PIWIK_URL
PIWIK_TOKEN = settings.PIWIK_TOKEN
PIWIK_SITEID = settings.PIWIK_SITEID

class PiwikMiddleware(object):
    @staticmethod
    def track_page_view(headers, title=None, userid=None, session_key=None, status_code=None):
        """
        Actually record the page view.

        Separated the real work so we can throw it in Celery.
        """
        req = FakeRequest(headers)
        pt = PiwikTracker(PIWIK_SITEID, req)
        pt.set_api_url(PIWIK_URL)
        pt.set_ip(get_real_ip(req))
        pt.set_token_auth(PIWIK_TOKEN)

        if session_key:
            visitor_id = hashlib.sha512(session_key).hexdigest()[0:PiwikTracker.LENGTH_VISITOR_ID]
            pt.set_visitor_id(visitor_id)

        if userid:
            pt.set_custom_variable(1, 'userid', userid, scope='visit')

        if status_code:
            pt.set_custom_variable(2, 'status_code', status_code, scope='page')

        pt.do_track_page_view(title)

    def process_response(self, request, response):
        if not PIWIK_URL or not PIWIK_TOKEN:
            # URL and TOKEN must be set to get us anywhere
            return

        # copy the META members that might actually be HTTP headers
        headers = dict((k,v) for k,v in request.META.iteritems() if isinstance(v, basestring))
        headers['HTTPS'] = request.is_secure()

        userid = request.user.username if request.user.is_authenticated() else None

        kwargs = {
            'headers': headers,
            'title': None,
            'userid': userid,
            'session_key': request.COOKIES.get(settings.SESSION_COOKIE_NAME, None),
            'status_code': response.status_code,
        }
        PiwikMiddleware.track_page_view(**kwargs)

        return response

