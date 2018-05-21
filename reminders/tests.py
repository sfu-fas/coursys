from django.test import TestCase
from django.urls import reverse
from courselib.testing import basic_page_tests


class RATest(TestCase):
    fixtures = ['basedata', 'coredata', 'reminders']

    def test_pages(self):
        """
        Test basic page rendering
        """
        c = Client()
        c.login_user('ggbaker')
