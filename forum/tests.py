from django.test import TestCase

from coredata.models import CourseOffering
from courselib.testing import Client, test_views, TEST_COURSE_SLUG
from forum.models import Forum


class ForumTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def setUp(self):
        o = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        self.offering = o
        f = Forum(offering=o)
        f.enabled = True
        f.save()

    def test_pages(self):
        """
        Render as many pages as possible, to make sure they work, are valid, etc.
        """
        c = Client()

        # test as an instructor
        c.login_user('ggbaker')
        test_views(self, c, 'offering:forum:',
                   ['index', 'new_thread', 'anon_identity'],
                   {'course_slug': self.offering.slug})

        # test as an instructor
        c.login_user('0aaa0')
        test_views(self, c, 'offering:forum:',
                   ['index', 'new_thread', 'anon_identity'],
                   {'course_slug': self.offering.slug})
