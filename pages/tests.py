# -*- coding: utf-8 -*-
from django.test import TestCase
from django.core.urlresolvers import reverse
from pages.models import Page, PageVersion, brushes_used
from coredata.models import CourseOffering, Member, Person
from courselib.testing import TEST_COURSE_SLUG, Client, test_views
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
    fixtures = ['test_data']
    def _get_creole(self):
        "Get a Creole class for some PageVersion for generic testing"
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        p = Page(offering=crs, label="Foo")
        p.save()
        pv = PageVersion(page=p)
        pv.get_creole()
        return pv.Creole
    
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
        brushes = brushes_used(Creole.parser.parse(wikitext))
        self.assertEqual(brushes, set(['shBrushJScript.js', 'shBrushPython.js']))
        
        html = Creole.text2html(wikitext)
        self.assertIn('class="brush: python">for i', html)
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
        url = reverse('pages.views.api_import', kwargs={'course_slug': crs.slug})
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
        
    def test_pages(self):
        """
        Basic page rendering
        """
        crs = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        memb = Member.objects.get(offering=crs, person__userid="ggbaker")
        person = Person.objects.get(userid='ggbaker')

        p = Page(offering=crs, label="Index")
        p.save()
        v = PageVersion(page=p, title="Index Page", wikitext="Original Contents", editor=memb)
        v.save()
        p = Page(offering=crs, label="OtherPage")
        p.save()
        v = PageVersion(page=p, title="Other Page", wikitext="Original Contents", editor=memb)
        v.save()
        
        c = Client()
        c.login_user('ggbaker')
        
        # test the basic rendering of the core pages
        test_views(self, c, 'pages.views.', ['index_page', 'all_pages', 'new_page', 'new_file', 'import_site'],
                {'course_slug': crs.slug})

        test_views(self, c, 'pages.views.', ['view_page', 'page_history', 'edit_page', 'import_page'],
                {'course_slug': crs.slug, 'page_label': 'OtherPage'})


