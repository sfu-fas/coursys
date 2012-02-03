import BeautifulSoup
import re

# TODO
# nested lists
# escape illegal URL chars
# insert escapes into strings where necessary http://www.wikicreole.org/wiki/EscapeCharacterProposal
# html5 header semantics would be nice
# use <title>
# maybe strip <header>, <footer>, <menu>?

blank_lines_re = re.compile(r'(\s*\n)(\s*\n)+')
any_whitespace = re.compile(r'\s+')

class HTML_to_Wiki(object):
    def __init__(self, options):
        """
        options should be a list/set/tuple selection of:
        'linkmarkup': is markup allowed in links? [[page.html|**bold link**]]
        """
        self.options = set(options)

    def handle_contents(self, elt, block, context=None):
        """
        Process contents of an element.
        """
        segments = [self.handle_element(e, context=context) for e in elt.contents]
        res = ''.join(segments)
        if block:
            res = '\n' + res.strip() + '\n'
        return res

    def process_li(self, elt, prefix):
        "Creole for an <li> (or other sub-structure markup)"
        return prefix + ' ' + self.handle_contents(elt, block=False).strip()

    def process_li_in(self, elt, prefix):
        "Creole for the <li>s in this list"
        lis = [self.process_li(e, prefix) for e in elt.contents if type(e)==BeautifulSoup.Tag and e.name=="li"]
        return '\n'.join(lis)
    
    def process_dl_item(self, elt):
        "Creole for a <dt> or <dd>"
        if elt.name == 'dt':
            prefix = ';'
        else:
            prefix = ':'
        
        return self.process_li(elt, prefix)

    def process_dl(self, elt):
        "Creole for a <dl>"
        lis = [self.process_dl_item(e) for e in elt.contents if type(e)==BeautifulSoup.Tag and e.name in ['dt', 'dd']]
        return '\n'.join(lis)

    def process_cell(self, elt):
        "Creole for a <td> or <th>"
        if elt.name == 'th':
            prefix = '|='
        else:
            prefix = '|'
        return self.process_li(elt, prefix)
        
    def process_tr(self, elt):
        "Creole for a <tr>"
        cells = [self.process_cell(e) for e in elt.contents if type(e)==BeautifulSoup.Tag and e.name in ['th', 'td']]
        return ' '.join(cells)
        
    def process_table(self, elt):
        "Creole for a <table>"
        rows = [self.process_tr(e) for e in elt.findAll('tr')]
        return '\n'.join(rows)


    def handle_tag(self, elt, context=None):
        if context=="textonly":
            return self.handle_contents(elt, block=False, context='textonly')
        if context=="pre":
            return self.handle_contents(elt, block=False, context='pre')
        
        name = elt.name
        if name in ['head', 'script', 'meta', 'link', 'style', 'title', 'input', 'button', 'select', 'option', 'optgroup', 'textarea', 'map', 'area', 'param', 'audio', 'video', 'canvas', 'datalist', 'embed', 'eventsource', 'keygen', 'progress', 'rp', 'rt', 'summary', 'source']:
            # tags whose content is ignored
            return ''
        elif name in ['html', 'body', 'form', 'div', 'p', 'address', 'noscript', 'fieldset', 'legend', 'h6', 'section', 'header', 'footer', 'article', 'hgroup', 'nav', 'aside', 'command', 'center']:
            # generic block tags
            return self.handle_contents(elt, block=True)
        elif name in ['ins', 'span', 'label', 'bdo', 'object', 'q', 'cite', 'kbd', 'samp', 'var', 'big', 'small', 'time', 'details', 'figcaption', 'figure', 'meter', 'mark', 'output', 'ruby', 'wbr']:
            # generic inline
            return self.handle_contents(elt,  block=False)
        elif name in ['h1', 'h2', 'h3', 'h4', 'h5']:
            level = int(name[1])
            return '\n%s %s %s\n' % ('='*level, self.handle_contents(elt, block=False), '='*level)
        elif name == 'blockquote':
            return '\n> ' + self.handle_contents(elt, block=False)
        elif name in ['strong', 'b']:
            return "**" + self.handle_contents(elt, block=False) + "**"
        elif name in ['em', 'i', 'dfn']:
            return "//" + self.handle_contents(elt, block=False) + "//"
        elif name == 'u':
            return "__" + self.handle_contents(elt, block=False) + "__"
        elif name in ['del', 'strike']:
            return "--" + self.handle_contents(elt, block=False) + "--"
        elif name in ['abbr', 'acronym']:
            try:
                title = elt['title']
                return "^" + self.handle_contents(elt, block=False) + ":" + title + "^"
            except KeyError:
                return "^" + self.handle_contents(elt, block=False) + "^"
        elif name == 'sup':
            return "^^" + self.handle_contents(elt, block=False) + "^^"
        elif name == 'sub':
            return ",," + self.handle_contents(elt, block=False) + ",,"
        elif name == 'pre':
            return '\n{{{' + self.handle_contents(elt, block=True, context='pre') + '}}}\n'
        elif name in ['tt', 'code']:
            return '##' + self.handle_contents(elt, block=False) + '##'
        elif name == 'hr':
            return '\n----\n'
        elif name == 'br':
            return r'\\'
        elif name in ['ul', 'menu']:
            return '\n' + self.process_li_in(elt, prefix="*") + '\n'
        elif name == 'ol':
            return '\n' + self.process_li_in(elt, prefix="#") + '\n'
        elif name == 'dl':
            return '\n' + self.process_dl(elt) + '\n'
        elif name == 'table':
            return '\n' + self.process_table(elt) + '\n'
        elif name in ['dt', 'dd', 'li']:
            # list items outside of their containers are treated as generic blocks
            return self.handle_contents(elt, block=True)
        elif name == 'img':
            try:
                url = elt['src']
                try:
                    alt = elt['alt']
                except KeyError:
                    alt = ''
                if alt.strip():
                    return '{{%s|%s}}' % (url, alt)
                else:
                    return '{{%s}}' % (url)
            except KeyError:
                return ''
        elif name == 'a':
            try:
                url = elt['href']
                if not url:
                    return self.handle_contents(elt, block=False)
                if 'linkmarkup' in self.options:
                    c = context
                else:
                    c = 'textonly'
                return '[[%s|%s]]' % (url, self.handle_contents(elt, block=False, context=c).strip().replace('\n', ' '))
            except KeyError:
                return self.handle_contents(elt, block=False)

        return '[unknown tag %s]' % (elt.name)


    def handle_element(self, elt, context=None):
        if elt is None:
            return ''
        elif type(elt) in [BeautifulSoup.Declaration, BeautifulSoup.Comment, BeautifulSoup.Declaration]:
            return ''
        elif isinstance(elt, basestring):
            if type(elt) == BeautifulSoup.CData:
                s = BeautifulSoup.NavigableString.__str__(elt)
            else:
                s = unicode(elt)
            
            if context == 'pre':
                return s
            else:
                return any_whitespace.sub(' ', s)
        elif type(elt) == BeautifulSoup.Tag:
            return self.handle_tag(elt, context=context)
        raise ValueError, str(type(elt))

    def from_soup(self, soup):
        """
        Convert a BeautifulSoup element to wikitext
        """
        segments = [self.handle_element(e) for e in soup.contents]
        res = ''.join(segments)
        res = blank_lines_re.sub('\n\n', res)
        return res.strip()
        
    def from_html(self, html):
        """
        Convert HTML source to wikitext
        """
        soup = BeautifulSoup.BeautifulSoup(html,
               convertEntities=BeautifulSoup.BeautifulSoup.XHTML_ENTITIES)
        return self.from_soup(soup)

filename = "index.html"
def main():
    parser = HTML_to_Wiki(['linkmarkup'])
    html = file(filename).read()
    wiki = parser.from_html(html)
    print wiki.encode('utf8')

main()

