from django.test import TestCase
from pages.models import Page, PageVersion, brushes_used, text2html, parser
from coredata.models import CourseOffering, Member
from courselib.testing import TEST_COURSE_SLUG
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
    def test_wiki_formatting(self):
        html = text2html("# one\n#two")
        html_strip = whitespace.sub('', html)
        self.assertEqual(html_strip, '<ol><li>one</li><li>two</li></ol>')

        html = text2html("good **times**")
        self.assertEqual(html, '<p>good <strong>times</strong></p>\n')

        # a WikiCreole "addition"
        html = text2html("; A\n: B\n; C: D")
        html_strip = whitespace.sub('', html)
        self.assertEqual(html_strip, '<dl><dt>A</dt><dd>B</dd><dt>C</dt><dd>D</dd></dl>')
        
    def test_codeblock(self):
        brushes = brushes_used(parser.parse(wikitext))
        self.assertEqual(brushes, set(['shBrushJScript.js', 'shBrushPython.js']))
        
        html = text2html(wikitext)
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
        

