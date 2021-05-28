from django.test import TestCase

from coredata.models import CourseOffering, Member
from courselib.testing import Client, test_views, TEST_COURSE_SLUG
from forum.models import Forum, REACTION_CHOICES, REACTION_ICONS, REACTION_SCORES, Thread, Post, Reply


class ForumTest(TestCase):
    fixtures = ['basedata', 'coredata']

    def setUp(self):
        o = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        self.offering = o
        f = Forum(offering=o)
        f.enabled = True
        f.save()

        instr = Member.objects.get(offering=o, person__userid='ggbaker')
        student = Member.objects.get(offering=o, person__userid='0aaa0')

        p = Post(offering=o, author=student, type='QUES')
        p.content = "Can I or not?\n\nI'm not really sure."
        p.markup = 'markdown'
        p.identity = 'INST'
        t = Thread(title='A Question', post=p)
        t.save()
        self.thread = t

        p = Post(offering=o, author=instr)
        p.content = 'Yeah, probably.'
        p.markup = 'markdown'
        p.identity = 'NAME'
        r = Reply(thread=t, parent=t.post, post=p)
        r.save()
        self.reply = r

    def test_coherence(self):
        all_reactions = set(k for k, v in REACTION_CHOICES)
        self.assertEqual(set(REACTION_ICONS.keys()), all_reactions)
        self.assertEqual(set(REACTION_SCORES.keys()), all_reactions)

    def test_pages(self):
        """
        Render as many pages as possible, to make sure they work, are valid, etc.
        """
        c = Client()

        # test as an instructor
        c.login_user('ggbaker')
        test_views(self, c, 'offering:forum:',
                   ['summary', 'new_thread', 'anon_identity'],
                   {'course_slug': self.offering.slug})
        test_views(self, c, 'offering:forum:',
                   ['view_thread'],
                   {'course_slug': self.offering.slug, 'post_number': self.thread.post.number})

        # test as a student
        c.login_user('0aaa0')
        test_views(self, c, 'offering:forum:',
                   ['summary', 'new_thread', 'anon_identity'],
                   {'course_slug': self.offering.slug})
        test_views(self, c, 'offering:forum:',
                   ['view_thread'],
                   {'course_slug': self.offering.slug, 'post_number': self.thread.post.number})
