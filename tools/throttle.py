from django.core.cache import cache
from django.http import HttpResponseForbidden

THROTTLE_TIME = 1      # minimum seconds between requests
EXCLUDE = ['/media/']  # path prefixes to exclude from limiting
REDIRS = set([301, 302, 303, 307])

class CacheThrottler(object):
    """
    A simple connection limiter.  Allows at most one connection every
    THROTTLE_TIME seconds.
    
    Uses the cache framework to store a flag that expires when the next
    request is allowed.
    """
    def request_key(self, request):
        # logged-in users throtted by userid; anonymous by IP address
        if hasattr(request, 'user') and not request.user.is_anonymous:
            userid = request.user.username
            return "throttle-"+userid
        else:
            remote_addr = request.META['REMOTE_ADDR']
            return "throttle-"+remote_addr
    
    def process_request(self, request):
        # ignore anything starting with an excluded path
        for prefix in EXCLUDE:
            if request.path.startswith(prefix):
                return

        key = self.request_key(request)
        if cache.get(key):
            return HttpResponseForbidden("Slow down.", content_type="text/plain")
        cache.set(key, True, THROTTLE_TIME)

    def process_response(self, request, response):
        # don't throttle after redirect, since immediate re-request is expected
        if response.status_code in REDIRS:
            key = self.request_key(request)
            cache.delete(key)

        return response
