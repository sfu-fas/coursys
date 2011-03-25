import re
import urlparse

# algorithm from http://notnotmobile.appspot.com/
# Some mobile browsers which look like desktop browsers.
RE_MOBILE = re.compile(r"(iphone|ipod|blackberry|android|palm|windows\s+ce|windows\s+phone)", re.I)
RE_DESKTOP = re.compile(r"(windows|linux|os\s+[x9]|solaris|bsd)", re.I)
RE_BOT = re.compile(r"(spider|crawl|slurp|bot)")

def _is_desktop(user_agent):
  """
  Anything that looks like a phone isn't a desktop.
  Anything that looks like a desktop probably is.
  Anything that looks like a bot should default to desktop.

  """
  return not bool(RE_MOBILE.search(user_agent)) and \
    bool(RE_DESKTOP.search(user_agent)) or \
    bool(RE_BOT.search(user_agent))

def _get_user_agent(request):
  # Some mobile browsers put the User-Agent in a HTTP-X header
  return request.META.get('HTTP_X_OPERAMINI_PHONE_UA') or \
         request.META.get('HTTP_X_SKYFIRE_PHONE') or \
         request.META.get('HTTP_USER_AGENT', '')
         
class MobileDetectionMiddleware(object):
    def process_request(self, request):
        if _is_desktop(_get_user_agent(request)):
            request.is_mobile = False
        else:
            request.is_mobile = True

            # If user switch between mobile/non-mobile, remember this with cookies 
            HTTP_REFERER = request.META.get('HTTP_REFERER')
            if HTTP_REFERER is None:
                return
            referer = urlparse.urlparse(HTTP_REFERER)
            uri = urlparse.urlparse(request.build_absolute_uri())
            if uri.netloc != referer.netloc:
                return

            # if from mobile to non-mobile, set Cookies
            if referer.path == "/m" + uri.path:
                # print 'mo -> no'
                request.COOKIES['no-mobile'] = 'Yes'
                request._new_cookies = True
            # if from non-mobile to mobile, remove Cookies
            elif "/m" + referer.path == uri.path:
                # print 'no -> mo'
                request.COOKIES['no-mobile'] = None
                request._new_cookies = True
            else:
                request._new_cookies = False
            
    def process_response(self, request, response):
        # set cookies for 'no-mobile'
        if 'no-mobile' in request.COOKIES\
            and hasattr(request, '_new_cookies') and request._new_cookies is True:
            # print 'set cookies!'
            if request.COOKIES['no-mobile'] == "Yes":
                response.set_cookie('no-mobile', 'Yes', max_age=3600*24*7) # for 7 days
            else:
                response.delete_cookie('no-mobile')
        return response

