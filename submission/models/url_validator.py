from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_text
import urllib.parse

class QuickURLValidator(URLValidator):
    """
    Subclass to add a timeout argument to the urllib2.urlopen call
    """

    def __call__(self, value):
        try:
            super(QuickURLValidator, self).__call__(value)
        except ValidationError as e:
            # Trivial case failed. Try for possible IDN domain
            if value:
                value = smart_text(value)
                scheme, netloc, path, query, fragment = urllib.parse.urlsplit(value)
                try:
                    netloc = netloc.encode('idna') # IDN -> ACE
                except UnicodeError: # invalid domain part
                    raise e
                url = urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))
                super(URLValidator, self).__call__(url)
            else:
                raise
        else:
            url = value

        if True: # self.verify_exists no longer exists, but we're doing it anyway.
            import urllib.request, urllib.error, urllib.parse
            headers = {
                "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                "Connection": "close",
                "User-Agent": 'CourSys',
            }
            try:
                req = urllib.request.Request(url, None, headers)
                u = urllib.request.urlopen(req, timeout=2)
            except ValueError:
                raise ValidationError('Enter a valid URL.', code='invalid')
            except: # urllib2.URLError, httplib.InvalidURL, etc.
                raise ValidationError('This URL appears to be a broken link.', code='invalid_link')

