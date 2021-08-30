import datetime

from django.test import TestCase

from coredata.models import CourseOffering, Member
from courselib.markup import convert_forum_links, markup_to_html
from courselib.testing import Client, test_views, TEST_COURSE_SLUG
from forum.models import Forum, REACTION_CHOICES, REACTION_ICONS, REACTION_SCORES, Thread, Post, Reply


class ForumLinkTest(TestCase):
    TEST_CASES = [
        # empty string
        ('', ''),
        # really simple
        ('x', 'x'),
        # basic link inserted
        ('<p>abc #123 &amp;def</p>', '<p>abc <a href="./123" class="xref">#123</a> &amp;def</p>'),
        # at start of text
        ('<p>#123X</p>', '<p><a href="./123" class="xref">#123</a>X</p>'),
        # at end of text
        ('<p>X#123</p>', '<p>X<a href="./123" class="xref">#123</a></p>'),
        # multiple links
        ('<p>one #1 two #2 <span>three #3</span></p>', '<p>one <a href="./1" class="xref">#1</a> two <a href="./2" class="xref">#2</a> <span>three <a href="./3" class="xref">#3</a></span></p>'),
        # entities (converted by minidom)
        ('<p>A&#123;B&amp;C&#x123;</p>', '<p>A{B&amp;Cģ</p>'),
        # ignore in <code>
        ('<p>abc #123 <code>def #456</code></p>', '<p>abc <a href="./123" class="xref">#123</a> <code>def #456</code></p>'),
        # ignore in <a>
        ('<div>a <a href="./">link #12</a> ignored #3</div>', '<div>a <a href="./">link #12</a> ignored <a href="./3" class="xref">#3</a></div>'),
        # no root element
        ('<p>A</p><p>A#123b</p>', '<p>A</p><p>A<a href="./123" class="xref">#123</a>b</p>'),
        # pathological markup: cdata and comments
        ('<div><![CDATA[#12 <b></b>]]></div><!-- #4 a -->', '<div><![CDATA[#12 <b></b>]]></div><!-- #4 a -->'),
    ]

    def test_markup_convert(self):
        # check correct output, from cases above
        for before, after in ForumLinkTest.TEST_CASES:
            result = convert_forum_links(before)
            self.assertEqual(after, result)

    def test_markup_skip(self):
        # if there's nothing like #123 anywhere in the markup, we expect to skip it entirely for efficiency. In that
        # case, we don't expect the fingerprints of a minidom parse and .toxml.

        # entity not converted if never touched.
        html = '<p>&#x30;</p>'
        result = convert_forum_links(html)
        self.assertEqual(result, '<p>&#x30;</p>')

        # false-positive on the initial regex search: parsed and reconstructed. ("&#x30;" becomes "0")
        html = '<p>&#x30; <a href="foo#123">x</a></p>'
        result = convert_forum_links(html)
        self.assertEqual(result, '<p>0 <a href="foo#123">x</a></p>')

    def test_markup_error(self):
        # test markup that generates a parse error: should be passed through unchanged
        html = '<p class="abc">&#x30;</q>'
        result = convert_forum_links(html)
        self.assertEqual(html, result)

    def test_full_path(self):
        # full markup_to_html test
        md = '## Hello\nSee #123 also.'
        html = markup_to_html(md, 'markdown', forum_links=False)
        self.assertEqual(html, '<h2>Hello</h2>\n<p>See #123 also.</p>')
        html = markup_to_html(md, 'markdown', forum_links=True)
        self.assertEqual(html, '<h2>Hello</h2>\n<p>See <a href="./123" class="xref">#123</a> also.</p>')

        # on a Post
        p = Post()
        p.content = 'See also #4, not `#5`.'
        p.markup = 'markdown'
        html = p.html_content()
        self.assertEqual(html, '<div class="tex2jax_ignore wikicontents"><p>See also <a href="./4" class="xref">#4</a>, not <code>#5</code>.</p></div>')


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
        self.offering.semester.end = datetime.date.today() + datetime.timedelta(days=90)
        self.offering.semester.save()
        c = Client()

        # test as an instructor
        c.login_user('ggbaker')
        test_views(self, c, 'offering:forum:',
                   ['summary', 'new_thread', 'identity', 'digest'],
                   {'course_slug': self.offering.slug})
        test_views(self, c, 'offering:forum:',
                   ['view_thread', 'edit_post'],
                   {'course_slug': self.offering.slug, 'post_number': self.thread.post.number})
        test_views(self, c, 'offering:forum:',
                   ['search'],
                   {'course_slug': self.offering.slug},
                   qs='q=test')

        # test as a student
        c.login_user('0aaa0')
        test_views(self, c, 'offering:forum:',
                   ['summary', 'new_thread', 'identity', 'digest'],
                   {'course_slug': self.offering.slug})
        test_views(self, c, 'offering:forum:',
                   ['view_thread', 'edit_post'],
                   {'course_slug': self.offering.slug, 'post_number': self.thread.post.number})
        test_views(self, c, 'offering:forum:',
                   ['search'],
                   {'course_slug': self.offering.slug},
                   qs='q=test')

