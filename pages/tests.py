# -*- coding: utf-8 -*-
from django.test import TestCase
from django.core.urlresolvers import reverse
from pages.models import Page, PageVersion, MACRO_LABEL, PagePermission
from coredata.models import CourseOffering, Member, Person
from grades.models import Activity
from courselib.testing import TEST_COURSE_SLUG, Client, test_views
from courselib.markup import ParserFor, markup_to_html
import re

wikitext = """Some Python code:
{{{ [python]

for i in range(4):
    print i


}}}

Some JavaScript code:
{{{[js]
for(i=1; i<4; i++) {
  document.write(i);
}
}}}
"""

contents1 = """Line that stays
Line that stays
Line that stays
Line that is changed
Line that is deleted
Line that stays
Line that stays
Line that stays
SEpARatoR
SEpARatoR
SEpARatoR
Line that is deleted
Line that stays
Line that is changed
Line that stays
SEpARatoR
SEpARatoR
SEpARatoR
Line that is deleted
Line that is changed
Line that stays
"""

contents2 = """New line at the start
Line that stays
Line that stays
Line that stays
Line that is modified
Line that stays
Line that stays
Line that was inserted
Line that stays
SEpARatoR
SEpARatoR
SEpARatoR
Line that stays
Line that was inserted
Line that is modified
Line that stays
SEpARatoR
SEpARatoR
SEpARatoR
Line that is changed
Line that stays
Line that was inserted
"""

contents3 = "This is just totally different content."

whitespace = re.compile(r"\s+")

class PagesTest(TestCase):
    fixtures = ['basedata', 'coredata']
    def _get_creole(self):
        "Get a Creole class for some PageVersion for generic testing"
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        p = Page(offering=crs, label="Foo")
        p.save()
        pv = PageVersion(page=p)
        return ParserFor(crs, pv)
    
    def test_wiki_formatting(self):
        Creole = self._get_creole()

        html = Creole.text2html("# one\n#two")
        html_strip = whitespace.sub('', html)
        self.assertEqual(html_strip, '<ol><li>one</li><li>two</li></ol>')

        html = Creole.text2html("good **times**")
        self.assertEqual(html, '<p>good <strong>times</strong></p>\n')

        # a WikiCreole "addition"
        html = Creole.text2html("; A\n: B\n; C: D")
        html_strip = whitespace.sub('', html)
        self.assertEqual(html_strip, '<dl><dt>A</dt><dd>B</dd><dt>C</dt><dd>D</dd></dl>')
        
    def test_codeblock(self):
        Creole = self._get_creole()
        #brushes = brushes_used(Creole.parser.parse(wikitext))
        #self.assertEqual(brushes, set(['shBrushJScript.js', 'shBrushPython.js']))
        
        html = Creole.text2html(wikitext)
        self.assertIn('class="highlight lang-python">for i', html)
        self.assertIn('print i</pre>', html)
        self.assertIn('i=1; i&lt;4; i++', html)

    def test_version_diffs(self):
        "Test the old version diffing."
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.get(offering=crs, person__userid="ggbaker")
        
        p = Page(offering=crs, label="Test")        
        p.save()
        v1 = PageVersion(page=p, title="T1", wikitext=contents1, editor=memb, comment="original page")
        v1.save()
        v2 = PageVersion(page=p, title="T2", wikitext=contents2, editor=memb, comment="some changes")
        v2.save()
        v3 = PageVersion(page=p, title="T3", wikitext=contents3, editor=memb, comment="total rewrite")
        v3.save()
        
        # refresh changes in DB
        v1 = PageVersion.objects.get(id=v1.id)
        v2 = PageVersion.objects.get(id=v2.id)
        v3 = PageVersion.objects.get(id=v3.id)
        
        # make sure the contents survived
        self.assertEqual(v1.get_wikitext(), contents1)
        self.assertEqual(v2.get_wikitext(), contents2)
        self.assertEqual(v3.get_wikitext(), contents3)
        self.assertEqual(v1.title, "T1")
        self.assertEqual(v2.title, "T2")
        self.assertEqual(v3.title, "T3")

        # make sure the diff got stored for incremental changes
        self.assertEqual(v1.wikitext, '')
        self.assertEqual(v1.diff_from_id, v2.id)
        
        # ... but big changes are stored verbatim
        self.assertEqual(v2.wikitext, contents2)
        self.assertEqual(v2.diff_from, None)

        # ... and the head has the current contents
        self.assertEqual(v3.wikitext, contents3)
        self.assertEqual(v3.diff_from, None)
    
    def test_api(self):
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.get(offering=crs, person__userid="ggbaker")
        person = Person.objects.get(userid='ggbaker')
        p = Page(offering=crs, label="PageExists")
        p.save()
        v = PageVersion(page=p, title="Page Exists", wikitext="Original Contents", editor=memb, comment="original page")
        v.save()
        
        from dashboard.models import new_feed_token
        token = new_feed_token()
        
        updata = u"""{
            "userid": "ggbaker",
            "token": "%s",
            "pages": [
                {
                    "label": "Index",
                    "title": "The Coursé Page",
                    "can_read": "ALL",
                    "can_write": "INST",
                    "wikitext-base64": "VGhpcyBwYWdlIGlzIHNwZWNpYWwgaW4gKipzb21lKiogd2F5LiBcKHh+XjIrMSA9IFxmcmFjezF9ezJ9XCkuCgpHb29kYnllIHdvcmxkIQ==",
                    "comment": "page creation comment",
                    "use_math": true
                },
                {
                    "label": "PageExists",
                    "new_label": "PageChanged",
                    "title": "Another Page",
                    "can_read": "STUD",
                    "wikitext": "This is some **new** page\\n\\ncontent."
                }
            ]
        }""" % (token)
        
        # make a request with no auth token in place
        c = Client()
        url = reverse('offering:pages:api_import', kwargs={'course_slug': crs.slug})
        response = c.post(url, data=updata.encode('utf8'), content_type="application/json")
        self.assertEquals(response.status_code, 403)
        
        # create token and try again
        person.config['pages-token'] = token
        person.save()
        response = c.post(url, data=updata.encode('utf8'), content_type="application/json")
        self.assertEquals(response.status_code, 200)
        
        # make sure the data arrived
        self.assertEquals(Page.objects.filter(offering=crs, label="PageExists").count(), 0)
        p = Page.objects.get(offering=crs, label="PageChanged")
        v = p.current_version()
        self.assertEqual(v.title, "Another Page")
        self.assertEqual(v.get_wikitext(), "This is some **new** page\n\ncontent.")
        
        p = Page.objects.get(offering=crs, label="Index")
        v = p.current_version()
        self.assertEqual(v.title, u"The Cours\u00e9 Page")
        self.assertEqual(v.get_wikitext(), 'This page is special in **some** way. \\(x~^2+1 = \\frac{1}{2}\\).\n\nGoodbye world!')
        self.assert_('math' in v.config)
        self.assertEqual(v.config['math'], True)

    def _sample_setup(self):
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.get(offering=crs, person__userid="ggbaker")

        p = Page(offering=crs, label="Index")
        p.save()
        v = PageVersion(page=p, title="Index Page", wikitext="Original Contents", editor=memb)
        v.save()
        p = Page(offering=crs, label="OtherPage")
        p.save()
        v = PageVersion(page=p, title="Other Page", wikitext="Original Contents", editor=memb)
        v.save()

        return crs

    def test_pages(self):
        """
        Basic page rendering
        """
        crs = self._sample_setup()
        c = Client()
        c.login_user('ggbaker')
        
        # test the basic rendering of the core pages
        test_views(self, c, 'offering:pages:', ['index_page', 'all_pages', 'new_page', 'new_file'],
                {'course_slug': crs.slug})

        test_views(self, c, 'offering:pages:', ['view_page', 'page_history', 'edit_page'],
                {'course_slug': crs.slug, 'page_label': 'OtherPage'})

    def test_permissions(self):
        """
        Test page access control behaviour.
        """
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.filter(offering=crs, role='INST').first()
        inst = memb.person
        ta = Member.objects.filter(offering=crs, role='TA').first().person
        stud = Member.objects.filter(offering=crs, role='STUD').first().person
        non_member = Person.objects.get(userid='dixon')
        assert not Member.objects.filter(offering=crs, person=non_member)

        p = Page(offering=crs, label="Test", can_read='STAF', can_write='INST')
        p.save()
        v = PageVersion(page=p, title="Test Page", wikitext="Page contents", editor=memb)
        v.save()

        # page-viewing permissions
        c = Client()
        url = reverse('offering:pages:view_page', kwargs={'course_slug': crs.slug, 'page_label': 'Test'})

        c.logout()
        response = c.get(url)
        self.assertEqual(response.status_code, 403)

        c.login_user(inst.userid)
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        c.login_user(ta.userid)
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        c.login_user(stud.userid)
        response = c.get(url)
        self.assertEqual(response.status_code, 403)

        c.login_user(non_member.userid)
        response = c.get(url)
        self.assertEqual(response.status_code, 403)

        # ... but with a PagePermission object, non_member can access
        pp = PagePermission(person=non_member, offering=crs, role='INST')
        pp.save()
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        # page-editing permissions
        url = reverse('offering:pages:edit_page', kwargs={'course_slug': crs.slug, 'page_label': 'Test'})

        c.logout()
        response = c.get(url)
        self.assertEqual(response.status_code, 302) # redirect to log in

        c.login_user(inst.userid)
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        c.login_user(ta.userid)
        response = c.get(url)
        self.assertEqual(response.status_code, 403)

        c.login_user(stud.userid)
        response = c.get(url)
        self.assertEqual(response.status_code, 403)

        # editing with PagePermission not implemented
        c.login_user(non_member.userid)
        response = c.get(url)
        self.assertEqual(response.status_code, 403)

    def test_form_submission(self):
        """
        Check that submitting the page editing form results in the objects we expect.
        """
        crs = self._sample_setup()
        c = Client()
        c.login_user('ggbaker')

        pg = Page.objects.get(offering=crs, label="Index")

        url = reverse('offering:pages:edit_page', kwargs={'course_slug': crs.slug, 'page_label': pg.label})
        form_data = {
            'offering': crs.id,
            'label': 'NewIndex',
            'can_read': 'ALL',
            'can_write': 'INST',
            'releasedate': '',
            'title': 'New Index',
            'markup_content_0': 'Unsafe <script>HTML</script>',
            'markup_content_1': 'html',
            'markup_content_2': 'on',
            'comment': 'the comment',
        }

        # bad submission: redisplay form
        resp = c.post(url, {})
        self.assertEqual(resp.status_code, 200)

        # good submission: save and redirect
        resp = c.post(url, form_data)
        self.assertEqual(resp.status_code, 302)

        pg = Page.objects.get(offering=crs, label="NewIndex")
        vr = pg.current_version()

        self.assertEqual(pg.can_write, 'INST')
        self.assertEqual(vr.title, 'New Index')
        self.assertEqual(vr.wikitext, 'Unsafe HTML') # should be cleaned on the way in
        self.assertEqual(vr.config['markup'], 'html')
        self.assertEqual(vr.config['math'], True)

    def test_macros(self):
        """
        Test macro behaviour
        """
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.get(offering=crs, person__userid="ggbaker")

        p = Page(offering=crs, label="Index")
        p.save()
        v = PageVersion(page=p, title="Index Page", wikitext="one +two+ three +four+", editor=memb)
        v.save()

        # no macros defined: rendered as-is
        self.assertEqual(p.current_version().html_contents().strip(), u"<p>one +two+ three +four+</p>")

        mp = Page(offering=crs, label=MACRO_LABEL)
        mp.save()
        mv = PageVersion(page=mp, title="Macros", wikitext="two: 22\nfour: 4444", editor=memb)
        mv.save()

        # macros defined: should be substituted
        self.assertEqual(p.current_version().html_contents().strip(), u"<p>one 22 three 4444</p>")

        mp.label = 'NOT_MACROS'
        mp.save()

        # macros disappear: back to original
        self.assertEqual(p.current_version().html_contents().strip(), u"<p>one +two+ three +four+</p>")


    def test_redirect(self):
        """
        Redirecting with redirect stub
        """
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.get(offering=crs, person__userid="ggbaker")

        p = Page(offering=crs, label="Test")
        p.save()
        v = PageVersion(page=p, title="Test Page", wikitext="one +two+ three +four+", editor=memb)
        v.save()

        c = Client()
        # normal pages still viewable
        url = reverse('offering:pages:view_page', kwargs={'course_slug': crs.slug, 'page_label': 'Test'})
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        v = PageVersion(page=p, redirect='NewLocation', editor=memb)
        v.save()

        response = c.get(url)
        self.assertEqual(response.status_code, 301)
        redir_url = reverse('offering:pages:view_page', kwargs={'course_slug': crs.slug, 'page_label': 'NewLocation'})
        self.assertTrue(response['location'].endswith(redir_url))


    def test_migration_redirect(self):
        """
        Redirecting after a migration
        """
        c = Client()
        c.login_user('0aaa0')

        # sample pages
        crs = self._sample_setup()
        # fake the course-has-been-migrated situation
        p = crs.page_set.exclude(label='Index').first()
        p.config['migrated_to'] = ['2000sp-subj-000-d1', 'PageLabel']
        p.can_read = 'ALL'
        p.save()
        url = reverse('offering:pages:view_page', kwargs={'course_slug': crs.slug, 'page_label': p.label})

        # without course setting, shouldn't redirect
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)

        # instructor said yes to redirects: make sure page redirects
        crs.config['redirect_pages'] = True
        crs.save()
        resp = c.get(url)
        self.assertEqual(resp.status_code, 301)

        # instructor should see a "this will usually redirect" message
        c.login_user('ggbaker')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('redirect_url', resp.context)

        # make sure prevent_redirect is honoured
        c.login_user('0aaa0')
        p.config['prevent_redirect'] = True
        p.save()
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_entity(self):
        """
        Test creole extension for HTML entities
        """
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        p = ParserFor(crs)

        # things that should be entities
        inp = u'&amp; &NotRightTriangle; &#8935; &#x1D54B;'
        outp = u'<p><span>&amp;</span> <span>&NotRightTriangle;</span> <span>&#8935;</span> <span>&#x1D54B;</span></p>'
        self.assertEquals(p.text2html(inp).strip(), outp)

        # things that should NOT be entities
        inp = u'&hello world; &#000000000123; &#x000000000123; &ThisIsAnAbsurdlyLongEntityNameThatWeDontWantToParse;'
        outp = u'<p>&amp;hello world; &amp;#000000000123; &amp;#x000000000123; &amp;ThisIsAnAbsurdlyLongEntityNameThatWeDontWantToParse;</p>'
        self.assertEquals(p.text2html(inp).strip(), outp)

    def test_extensions(self):
        """
        Test creole macros we have defined
        """
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        p = ParserFor(crs)
        a1 = Activity.objects.get(offering=crs, slug='a1')

        html = p.text2html('one <<duedate A1>> two')
        self.assertIn('>' + a1.due_date.strftime('%A %B %d %Y') + '<', html)

        html = p.text2html('one <<duedatetime A1>> two')
        self.assertIn('>' + a1.due_date.strftime('%A %B %d %Y, %H:%M') + '<', html)

        html = p.text2html(u'one <<activitylink A1>> two')
        link = u'<a href="%s">%s' % (a1.get_absolute_url(), a1.name)
        self.assertIn(link.encode('utf-8'), html)

    def test_markup_choice(self):
        """
        Check the distinction between Creole and Markdown pages
        """
        offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.get(offering=offering, person__userid="ggbaker")

        p = Page(offering=offering, label="Test")
        p.save()
        v1 = PageVersion(page=p, title="T1", wikitext='A //test//.', editor=memb, comment="original page")
        v1.save()
        self.assertEqual(v1.html_contents(), '<p>A <em>test</em>.</p>')

        v2 = PageVersion(page=p, title="T1", wikitext='A *test*.', editor=memb, comment="original page")
        v2.set_markup('markdown')
        v2.save()
        self.assertEqual(v2.html_contents(), '<p>A <em>test</em>.</p>')

    def test_github_markdown(self):
        """
        Check that we're getting the Github markdown flavour.
        """
        highlighted_code = markup_to_html('```python\ni=1\n```', 'markdown')
        self.assertEqual(highlighted_code, '<pre lang="python"><code>i=1\n</code></pre>')

    def test_html_safety(self):
        """
        Check that we're handling HTML in a safe way
        """
        html = markup_to_html('<p>Foo</em>', 'html')
        self.assertEqual(html, '<p>Foo</p>')

        html = markup_to_html('Foo<script>alert()</script>', 'html')
        self.assertEqual(html, 'Fooalert()')

        # unsafe if we ask for it
        html = markup_to_html('Foo<script>alert()</script>', 'html', html_already_safe=True)
        self.assertEqual(html, 'Foo<script>alert()</script>')

        # PageVersions should be saved only with safe HTML
        offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.get(offering=offering, person__userid="ggbaker")

        p = Page(offering=offering, label="Test")
        p.save()
        v1 = PageVersion(page=p, title="T1", wikitext='<em>Some</em> <script>HTML</script>', editor=memb)
        v1.set_markup('html')
        v1.save()

        self.assertEqual(v1.wikitext, '<em>Some</em> HTML')
