import datetime
import time
import logging

from django.core.exceptions import PermissionDenied, BadRequest, SuspiciousOperation
from django.db import connection
from django.http import HttpRequest, HttpResponse, Http404
from django.http.multipartparser import MultiPartParserError
from django.urls.resolvers import ResolverMatch
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from ipware import get_client_ip

from log.models import RequestLog

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


# adapted from  https://gist.github.com/fabiosussetto/c534d84cbbf7ab60b025
class NonHtmlDebugToolbarMiddleware(object):
    """
    The Django Debug Toolbar usually only works for views that return HTML.
    This middleware wraps any JSON response in HTML if the request
    has a 'debug' query parameter (e.g. http://localhost/foo?debug)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import json
        from django.http import HttpResponse
        from django.utils.html import escape
        response = self.get_response(request)
        if request.GET.get('debug'):
            if response['Content-Type'] == 'application/json':
                content = json.dumps(json.loads(response.content), sort_keys=True, indent=2)
                response = HttpResponse(u'<html><body><pre>{}</pre></body></html>'.format(escape(content)))
        return response


class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.start = None
        self.logged_exception = False

    def request_log(self, request: HttpRequest) -> RequestLog:
        """
        Build basic RequestLog for this request.
        """
        ip, _ = get_client_ip(request)
        username = request.user.username if request.user.is_authenticated else None
        request_id = request.META.get('HTTP_X_REQUEST_ID', None)
        referer = request.META.get('HTTP_REFERER', None)
        user_agent = request.META.get('HTTP_USER_AGENT', None)
        session_key = request.session.session_key if request.session and request.session.session_key else None
        if 'CONTENT_LENGTH' in request.META and request.META['CONTENT_LENGTH'].isnumeric():
            request_content_length = int(request.META['CONTENT_LENGTH'])
        else:
            request_content_length = 0

        log_data = {
            'query_string': request.META.get('QUERY_STRING', ''),
            'ip': ip,
            'user_agent': user_agent,
            'referer': referer,
            'request_id': request_id,
            'session_key': session_key,
            'request_content_length': request_content_length,
            #'n_queries': len(connection.queries),  # connection.queries is only available when DEBUG==True
        }

        if hasattr(request, 'resolver_match') and isinstance(request.resolver_match, ResolverMatch):
            log_data['view_name'] = request.resolver_match.view_name

        return RequestLog(
            time=self.start,
            duration=datetime.datetime.now() - self.start,
            username=username,
            path=request.path,
            method=request.method,
            data=log_data
        )

    def __call__(self, request):
        self.start = datetime.datetime.now()
        response = self.get_response(request)

        # exceptions are logged in process_exception: don't double-log
        if not self.logged_exception:
            log = self.request_log(request)
            log.data['status_code'] = response.status_code
            log.data['response_content_type'] = response.headers.get('Content-Type', None)
            if 'Location' in response:
                log.data['redirect-location'] = response['Location']

            try:
                if isinstance(response, HttpResponse):  # exclude streaming responses
                    log.data['response_content_length'] = sum(len(c) for c in response._container)
            except Exception:
                pass  # don't throw if the internal ._container implementation changes

            log.save()

        self.logged_exception = False
        return response

    def process_exception(self, request, exception):
        # Ignore exceptions that are converted to some other response by
        # django.core.handlers.exception.response_for_exception and treat them as "regular" responses.
        if isinstance(exception, (Http404, PermissionDenied, MultiPartParserError, BadRequest, SuspiciousOperation)):
            return

        log = self.request_log(request)
        log.data['exception'] = exception.__class__.__name__
        log.data['exception_message'] = str(exception)
        log.data['status_code'] = 500
        log.save()

        self.logged_exception = True
