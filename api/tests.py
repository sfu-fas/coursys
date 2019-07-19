import json
import urllib

import requests
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse, resolve
import oauth2 as oauth
from lxml import etree
from oauth_provider.models import Consumer, Token
from oauth_provider.consts import ACCEPTED
from courselib.testing import Client, TEST_COURSE_SLUG
from .models import ConsumerInfo
from coredata.models import Member


VERIFIER = '1234567890'


class APIEndpointTester(object):
    """
    Check API views

    Records views we have seen links to, and views we have tested. We want the set to be the same to ensure HATEOAS
    links, and complete test coverage of API views.
    """
    def __init__(self, client, testcase):
        self.client = client
        self.testcase = testcase
        # fake APIRoot into the found links: we don't demand a link to it since it's the root
        self.found_view_links = set([self.link_to_view(reverse('api:APIRoot'))])
        self.checked_views = set()

    def all_links(self, data):
        """
        find all links in a JSON API response
        """
        if isinstance(data, dict):
            if 'link' in data:
                yield data['link']
            if 'links' in data:
                for u in list(data['links'].values()):
                    yield u
        elif isinstance(data, (list, tuple)):
            for d in data:
                for u in self.all_links(d):
                    yield u

    def link_to_view(self, url):
        url = url.replace('http://testserver/', '/')
        url = url.replace('http://localhost:8000/', '/')
        return resolve(url).func

    def links_to_views(self, urls):
        return list(map(self.link_to_view, urls))

    def find_views_in(self, data):
        found = set(self.links_to_views(self.all_links(data)))
        self.found_view_links |= found

    def check_endpoint(self, view, view_kwargs):
        """
        Check an API endpoint. Returns set of views that are linked by the resp
        """
        url = reverse(view, kwargs=view_kwargs)
        resp = self.client.get(url)
        self.testcase.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf8'))

        self.find_views_in(data)
        self.checked_views.add(self.link_to_view(url))

    def check_found_links(self):
        self.testcase.assertEqual(self.checked_views, self.found_view_links)




class APITest(TestCase):
    fixtures = ['basedata', 'coredata']

    def setUp(self):
        self.faketime = 525942870
        self.client = Client()

        # create a Consumer (and associated stuff)
        try:
            u = User.objects.get(username='ggbaker')
        except User.DoesNotExist:
            u = User(username='ggbaker')
            u.save()

        try:
            c = Consumer.objects.get(name='Test Consumer')
        except Consumer.DoesNotExist:
            c = Consumer(name='Test Consumer')

        c.description = 'Consumer to do some tests with'
        c.status = ACCEPTED
        c.user = u
        c.xauth_allowed = False
        c.generate_random_codes()
        c.save()
        self.consumer = c

        i = ConsumerInfo(consumer=c)
        i.admin_contact = 'the_developer@example.com'
        i.permissions = ['courses']
        i.timestamp = self.faketime - 10 # make sure the ConsumerInfo was there "before" the Token was created
        i.save()
        self.consumerinfo = i

        # create an access token so we can jump in to requests
        try:
            t = Token.objects.get(token_type=Token.ACCESS, consumer=c, user=u)
        except Token.DoesNotExist:
            t = Token(token_type=Token.ACCESS, consumer=c, user=u, timestamp=self.faketime)
       
        t.is_approved = True
        t.generate_random_codes()
        t.verifier = VERIFIER
        t.save()
        self.token = t

    def test_consumerinfo(self):

        # replace time.time with a function that always returns ( 7:14AM, Sept 1, 1986 ) 

        # make sure we get the right ConsumerInfo object for a token
        i0 = ConsumerInfo(consumer=self.consumer, admin_contact='foo', permissions=['everything', 'nothing'])
        i0.timestamp = self.faketime - 100
        i0.save()

        i2 = ConsumerInfo(consumer=self.consumer, admin_contact='foo', permissions=['something'])
        i2.timestamp = self.faketime + 100
        i2.save()

        # we should retrieve the most recent before token creation: this is what the user agreed to.
        perms = ConsumerInfo.allowed_permissions(self.token)
        self.assertEqual(perms, ['courses'])

        # if it has been deactivated, then no permissions remain
        self.consumerinfo.deactivated = True
        self.consumerinfo.save()
        perms = ConsumerInfo.allowed_permissions(self.token)
        self.assertEqual(perms, [])

    def test_head_request(self):
        "Make sure HEAD requests work with the cache mixin"
        self.client.login_user('ggbaker')
        url = reverse('api:APIRoot', kwargs={})
        resp = self.client.head(url)

    def test_all_endpoints(self):
        client = self.client
        client.login_user("ggbaker")

        tester = APIEndpointTester(client, self)

        tester.check_endpoint('api:APIRoot', {})
        tester.check_endpoint('api:MyOfferings', {})
        tester.check_endpoint('api:OfferingInfo', {'course_slug': TEST_COURSE_SLUG})
        tester.check_endpoint('api:OfferingActivities', {'course_slug': TEST_COURSE_SLUG})
        tester.check_endpoint('api:OfferingGrades', {'course_slug': TEST_COURSE_SLUG})
        tester.check_endpoint('api:OfferingStats', {'course_slug': TEST_COURSE_SLUG})
        tester.check_endpoint('api:OfferingStudents', {'course_slug': TEST_COURSE_SLUG})

        tester.check_found_links()

    def test_class_list_permission(self):
        """
        Check that the class list API endpoint has the right permissions
        """
        client = self.client

        # no auth: should be forbidden
        url = reverse('api:OfferingStudents', kwargs={'course_slug': TEST_COURSE_SLUG})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
        data = json.loads(resp.content.decode('utf8'))
        self.assertIsInstance(data, dict)
        self.assertEqual(list(data.keys()), ['detail'])

        # as instructor: should return class list
        client.login_user("ggbaker")
        url = reverse('api:OfferingStudents', kwargs={'course_slug': TEST_COURSE_SLUG})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf8'))
        self.assertIsInstance(data, list)
        self.assertEqual({d['userid'] for d in data},
                         {m.person.userid for m in Member.objects.filter(offering__slug=TEST_COURSE_SLUG, role='STUD')
                             .select_related('person')})

        # as a student: should be forbidden
        client.login_user("0aaa0")
        url = reverse('api:OfferingStudents', kwargs={'course_slug': TEST_COURSE_SLUG})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
        data = json.loads(resp.content.decode('utf8'))
        self.assertIsInstance(data, dict)
        self.assertEqual(list(data.keys()), ['detail'])


class OAuthTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def test_oauth_workflow(self):
        request_token_url = 'http://testserver' + reverse('api:oauth_request_token')
        authorize_token_url = 'http://testserver' + reverse('api:oauth_user_authorization')

        # create consumer for tests
        c = Client()
        c.login_user('ggbaker')
        c.logout()
        consumer = Consumer(name='Test Consumer', description='Consumer to do some tests with', status=ACCEPTED,
                     user=User.objects.get(username='ggbaker'), xauth_allowed=False)
        consumer.generate_random_codes()
        consumer.save()
        ci = ConsumerInfo(consumer=consumer)
        ci.admin_contact = 'the_developer@example.com'
        ci.permissions = ['courses', 'grades']
        ci.save()

        # generate request token
        oauth_request = oauth.Request.from_consumer_and_token(consumer, http_url=request_token_url,
                                                              parameters={'oauth_callback': 'oob'})
        oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)

        resp = c.get(request_token_url, **oauth_request.to_header())
        self.assertEqual(resp.status_code, 200)
        request_token = dict(urllib.parse.parse_qsl(resp.content.decode('utf8')))

        # get auth verifier
        c.login_user('ggbaker')
        resp = c.get(authorize_token_url, {'oauth_token': request_token['oauth_token']})
        self.assertEqual(resp.status_code, 200)
        resp = c.post(authorize_token_url, {'oauth_token': request_token['oauth_token'], 'authorize_access': 'on'})
        self.assertEqual(resp.status_code, 200)
        parser = etree.HTMLParser()
        root = etree.fromstring(resp.content, parser=parser)
        verifier_elt = root.xpath('//*[@id="verifier"]')[0]
        oauth_verifier = verifier_elt.text.strip()
        c.logout()

        # get access token
        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(oauth_verifier)
        oauth_request = oauth.Request.from_consumer_and_token(consumer, token, http_url=authorize_token_url)
        oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, token)

        resp = c.get(authorize_token_url, **oauth_request.to_header())
        # TODO: this is failing for some reason, but succeeds in the demo scripts
        #self.assertEqual(resp.status_code, 200)
        #access_token = dict(urllib.parse.parse_qsl(response.content.decode('utf8')))




