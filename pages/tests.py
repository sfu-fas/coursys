from django.test import TestCase
from pages.models import Page, PageVersion, brushes_used, text2html, parser
import re

wikitext = """Some Python code:
{{{ #!python
for i in range(4):
    print i
}}}

Some JavaScript code:
{{{#!js
for(i=1; i<4; i++) {
  document.write(i);
}
}}}
"""

whitespace = re.compile(r"\s+")

class SimpleTest(TestCase):
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
        self.assertIn('i=1; i&lt;4; i++', html)

        
