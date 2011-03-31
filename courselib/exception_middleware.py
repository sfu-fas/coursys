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
