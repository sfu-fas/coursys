# inspiration from http://djangosnippets.org/snippets/638/

#from django.conf import settings
#from django.core.mail import mail_admins

import sys
logfile = "/tmp/django-errors.txt"

class ExceptionMiddleware(object):
    def process_exception(self, request, exception):
        exc_info = sys.exc_info()

        try:
            request_repr = repr(request)
        except:
            request_repr = "Request repr() unavailable"
        
        fh = open(logfile, "a")
        fh.write("\n")
        fh.write("="*70)
        fh.write("\n")
        fh.write(_get_traceback(exc_info))
        fh.write("\n\n")
        fh.write(request_repr)
        fh.write("\n")
        fh.close()


def _get_traceback(self, exc_info=None):
    """Helper function to return the traceback as a string"""
    import traceback
    return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))


import time
import logging
from django.db import connection
from django.conf import settings
logger = logging.getLogger(__name__)

class MonitoringMiddleware(object):
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



from courselib.auth import HttpError
class ExceptionIgnorer(object):
    """
    Middleware to eat the exception that we really don't need to see.
    """
    def process_exception(self, request, exception):
        import traceback
        exc_info = sys.exc_info()
        format = traceback.format_exc(exc_info[2])
        message = unicode(exception)
        if isinstance(exception, IOError) and 'Connection reset by peer' in message and '_verify(ticket, service)' in format:
            # CAS verification timeout
            return HttpError(request, status=500, title="CAS Error", error="Could not contact the CAS server to verify your credentials. Please try logging in again.")
        elif isinstance(exception, EOFError) and "return request.POST.get('csrfmiddlewaretoken', '')" in format:
            # file upload EOF
            return HttpError(request, status=500, title="Upload Error", error="Upload seems to have not completed properly.")



