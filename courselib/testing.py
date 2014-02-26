import os
import urllib
import html5lib
from django.core.urlresolvers import reverse

# course with the test data
TEST_COURSE_SLUG = '2014sp-cmpt-165-c1'

def validate_content_xhtml(testcase, data, page_descr="unknown page"):
    """
    Validate data as XHTML 1.0 (strict).
    
    testcase should be a unittest.TestCase object (or similar).
    page_descr should be a human-readable description of the page being tested.
    """
    from lxml import etree
    # force use of local copy of DTD
    dtdpath = os.path.join(os.getcwd(), "courselib", "dtd", "xhtml1-strict.dtd")
    dtdpath = dtdpath.replace("\\", "/")
    dtdpath = urllib.quote(dtdpath)
    
    dtd = '<!DOCTYPE html SYSTEM "%s">' % dtdpath
    data_system = data.replace('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">', dtd, 1)
    assert data != data_system
    
    try:
        parser = etree.XMLParser(dtd_validation=True, no_network=True)
        etree.fromstring(data_system, parser=parser)
    except etree.XMLSyntaxError as e:
        #print "-"*40
        #print data
        #print "-"*40
        fh = open("tmp-validation.html", "w")
        fh.write(data)
        fh.close()
        testcase.fail("Invalid XHTML produced in %s:\n  %s" % (page_descr, str(e)))


def validate_content(testcase, data, page_descr="unknown page"):
    """
    Validate data as HTML5.

    testcase should be a unittest.TestCase object (or similar).
    page_descr should be a human-readable description of the page being tested.
    """
    parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("dom"))
    parser.parse(data)
    if parser.errors:
        fh = open("tmp-validation.html", "w")
        fh.write(data)
        fh.close()
        testcase.fail("Invalid HTML5 produced in %s:\n  %s" % (page_descr, str(parser.errors)))



def basic_page_tests(testcase, client, url, check_valid=True):
    """
    Run basic tests on the page: 200 OK, validity.
    """
    response = client.get(url)
    testcase.assertEquals(response.status_code, 200)
    if check_valid:
        validate_content(testcase, response.content, url)
    return response

def test_auth(client, userid):
    """
    Login as this user for testing
    """
    client.get(reverse('dashboard.views.fake_login') + '?userid=' + 'ggbaker')

def test_views(testcase, client, view_prefix, views, url_args, qs=None):
    """
    Test a collection of views, just to make sure they render
    """
    for v in views:
        view = view_prefix + v
        try:
            url = reverse(view, kwargs=url_args)
            if qs:
                url += '?' + qs
            response = basic_page_tests(testcase, client, url)
        except Exception as e:
            print "failing with view=" + view
            raise



from django.conf import settings
from django.contrib.auth.models import User
from importlib import import_module
from django.http import HttpRequest
from django.contrib.auth import login
from django.test.client import Client as OriginalClient


# Adapted from http://jameswestby.net/weblog/tech/17-directly-logging-in-a-user-in-django-tests.html
# adds the login_user method that just logs some existing user in.
class Client(OriginalClient):
    def login_user(self, userid):
        """
        Login as specified user, does not depend on auth backend (hopefully)

        This is based on Client.login() with a small hack that does not
        require the call to authenticate()
        """
        if not 'django.contrib.sessions' in settings.INSTALLED_APPS:
            raise AssertionError("Unable to login without django.contrib.sessions in INSTALLED_APPS")
        try:
            user = User.objects.get(username=userid)
        except User.DoesNotExist:
            user = User(username=userid, password='')
            user.save()
        user.backend = "%s.%s" % ("django.contrib.auth.backends",
                                  "ModelBackend")
        engine = import_module(settings.SESSION_ENGINE)

        # Create a fake request to store login details.
        request = HttpRequest()
        if self.session:
            request.session = self.session
        else:
            request.session = engine.SessionStore()
        login(request, user)

        # Set the cookie to represent the session.
        session_cookie = settings.SESSION_COOKIE_NAME
        self.cookies[session_cookie] = request.session.session_key
        cookie_data = {
            'max-age': None,
            'path': '/',
            'domain': settings.SESSION_COOKIE_DOMAIN,
            'secure': settings.SESSION_COOKIE_SECURE or None,
            'expires': None,
        }
        self.cookies[session_cookie].update(cookie_data)

        # Save the session values.
        request.session.save()
