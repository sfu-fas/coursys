from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class QuickURLValidator(URLValidator):
    """
    Subclass to add a timeout argument to the urllib2.urlopen call
    """

    def __call__(self, value):
        try:
            super(QuickURLValidator, self).__call__(value)
        except ValidationError, e:
            # Trivial case failed. Try for possible IDN domain
            if value:
                value = smart_unicode(value)
                scheme, netloc, path, query, fragment = urlparse.urlsplit(value)
                try:
                    netloc = netloc.encode('idna') # IDN -> ACE
                except UnicodeError: # invalid domain part
                    raise e
                url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
                super(URLValidator, self).__call__(url)
            else:
                raise
        else:
            url = value

        if self.verify_exists:
            import urllib2
            headers = {
                "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                "Connection": "close",
                "User-Agent": self.user_agent,
            }
            try:
                req = urllib2.Request(url, None, headers)
                u = urllib2.urlopen(req, timeout=2)
            except ValueError:
                raise ValidationError(u'Enter a valid URL.', code='invalid')
            except: # urllib2.URLError, httplib.InvalidURL, etc.
                raise ValidationError(u'This URL appears to be a broken link.', code='invalid_link')

