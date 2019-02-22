import time
import logging
from django.db import connection
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
logger = logging.getLogger(__name__)

class MonitoringMiddleware(MiddlewareMixin):
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

class ExceptionIgnorer(MiddlewareMixin):
    """
    Middleware to eat the exception that we really don't need to see.
    """
    def process_exception(self, request, exception):
        import traceback
        exc_info = sys.exc_info()
        try:
            format = traceback.format_exc(exc_info[2])
        except:
            format = ''
        message = str(exception)
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