import BeautifulSoup
import re

# TODO
# nested lists
# escape illegal URL chars
# escape CamelCase text
# html5 header semantics would be nice
# use <title>
# maybe strip <header>, <footer>, <menu>?

class HTMLWiki(object):
    blank_lines_re = re.compile(r'(\s*\n)(\s*\n)+') # used to remove extra blank lines
    any_whitespace = re.compile(r'\s+') # used to collapse whitespace in text
    block_markup_re = re.compile(r'^\s*(=+|\*|#|;|:|----)') # used to escape wiki markup in text
    inline_markup_re = re.compile(r'(~+|\*|//+|__+|-|\^+|,,+|\{|\}|##+|\\\\+|\[\[+|]]+)')

    class ParseError(Exception):
        pass

    tag_handler = {} # dictionary of tag -> output-producing function

    def __init__(self, options):
        """
        options should be a list/set/tuple selection of:
        'linkmarkup': is markup allowed in links? [[page.html|**bold link**]]
        """
        self.options = set(options)
        self.setup_handlers()
        
    def wiki_escape(self, txt):
        """
        Escape text so any wiki formatting-like text doesn't actually format.
        """
        txt = self.inline_markup_re.sub(r'~\1', txt) # occurs-anywhere patterns
        txt = self.block_markup_re.sub(r'~\1', txt) # start-of-line patterns
        return txt

    def url_escape(self, url):
        """
        Make sure URLs are escaped to remove any wiki markup
        """
        url = url.replace(']', '%5D')
        url = url.replace('|', '%7C')
        url = url.replace('}', '%7D')
        return url

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
        return prefix + ' ' + self.handle_contents(elt, block=False, context='list'+prefix).strip()

    def process_li_in(self, elt, prefix, context=None):
        "Creole for the <li>s in this list"
        prev = ''
        if context and context.startswith('list'):
            # context is indicating we're a sub-list: honour the prefix.
            prev = context[4:]

        lis = [self.process_li(e, prev+prefix) for e in elt.contents if type(e)==BeautifulSoup.Tag and e.name=="li"]
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

    # tag handlers referenced in self.tag_handler
    def handler_ignore_contents(self, elt, context):
        return ''
    def handler_generic_block(self, elt, context):
        return self.handle_contents(elt, block=True)
    def handler_generic_inline(self, elt, context):
        return self.handle_contents(elt, block=False)
    def handler_simple_inline(self, markup):
        def handler(elt, context):
            return markup + self.handle_contents(elt, block=False) + markup
        return handler
    def handler_heading(self, elt, context):
        level = int(elt.name[1])
        return '\n%s %s %s\n' % ('='*level, self.handle_contents(elt, block=False), '='*level)
    def handler_abbr(self, elt, context):
        try:
            title = elt['title']
            return "^" + self.handle_contents(elt, block=False) + ":" + title + "^"
        except KeyError:
            return "^" + self.handle_contents(elt, block=False) + "^"
    def handler_pre(self, elt, context):    
        return '\n{{{' + self.handle_contents(elt, block=True, context='pre') + '}}}\n'
    def handler_ul(self, elt, context):
        return '\n' + self.process_li_in(elt, prefix="*", context=context) + '\n'
    def handler_ol(self, elt, context):
        return '\n' + self.process_li_in(elt, prefix="#", context=context) + '\n'
    def handler_dl(self, elt, context):
        return '\n' + self.process_dl(elt) + '\n'
    def handler_table(self, elt, context):
        return '\n' + self.process_table(elt) + '\n'
    def handler_img(self, elt, context):
        try:
            url = self.url_escape(elt['src'])
            try:
                alt = elt['alt']
            except KeyError:
                alt = ''

            if alt.strip():
                # pseudo-escape alt text
                alt = alt.replace('}}', u'}\uFEFF}') # unicode zero width no-break space
                if alt[-1] == '}':
                    alt += u'\uFEFF'
                return '{{%s|%s}}' % (url, alt)
            else:
                return '{{%s}}' % (url)
        except KeyError:
            return ''
    def handler_link(self, elt, context):
        try:
            url = self.url_escape(elt['href'])
            if not url:
                return self.handle_contents(elt, block=False)
            if 'linkmarkup' in self.options:
                c = context
            else:
                c = 'textonly'

            # pseudo-escape content text
            content = self.handle_contents(elt, block=False, context=c).strip()
            content = content.replace(']]', u']\uFEFF]') # unicode zero width no-break space
            if content and content[-1] == ']':
                    content += u'\uFEFF'

            #print ">>>", url
            self.urls.add(url)
            return '[[%s|%s]]' % (url, content)
        except KeyError:
            return self.handle_contents(elt, block=False)
        

    def setup_handlers(self):
        """
        Populates the self.tag_handler dictionary of ways to tranlate a tags to wikitext.
        """
        for elt in ['head', 'script', 'meta', 'link', 'style', 'title', 'input',
                    'button', 'select', 'option', 'optgroup', 'textarea', 'map',
                    'area', 'param', 'audio', 'video', 'canvas', 'datalist', 'embed',
                    'eventsource', 'keygen', 'progress', 'rp', 'rt', 'summary', 'source']:
            self.tag_handler[elt] = self.handler_ignore_contents
        for elt in ['html', 'body', 'form', 'div', 'p', 'address', 'noscript',
                    'fieldset', 'legend', 'h6', 'section', 'header', 'footer', 'article',
                    'hgroup', 'nav', 'aside', 'command', 'center', 'dt', 'dd', 'li']:
            self.tag_handler[elt] = self.handler_generic_block
        for elt in ['ins', 'span', 'label', 'bdo', 'object', 'q', 'cite', 'kbd', 'samp',
                    'var', 'big', 'small', 'time', 'details', 'figcaption', 'figure',
                    'meter', 'mark', 'output', 'ruby', 'wbr', 'font']:
            self.tag_handler[elt] = self.handler_generic_inline
        for elt in ['h1', 'h2', 'h3', 'h4', 'h5']:
            self.tag_handler[elt] = self.handler_heading

        self.tag_handler['abbr'] = self.handler_abbr
        self.tag_handler['acronym'] = self.handler_abbr
        self.tag_handler['pre'] = self.handler_pre
        self.tag_handler['ul'] = self.handler_ul
        self.tag_handler['menu'] = self.handler_ul
        self.tag_handler['ol'] = self.handler_ol
        self.tag_handler['dl'] = self.handler_dl
        self.tag_handler['table'] = self.handler_table
        self.tag_handler['pre'] = self.handler_pre
        self.tag_handler['img'] = self.handler_img
        self.tag_handler['a'] = self.handler_link
        
        self.tag_handler['strong'] = self.handler_simple_inline('**')
        self.tag_handler['b'] = self.handler_simple_inline('**')
        self.tag_handler['em'] = self.handler_simple_inline('//')
        self.tag_handler['i'] = self.handler_simple_inline('//')
        self.tag_handler['dfn'] = self.handler_simple_inline('//')
        self.tag_handler['u'] = self.handler_simple_inline('__')
        self.tag_handler['del'] = self.handler_simple_inline('--')
        self.tag_handler['strike'] = self.handler_simple_inline('--')
        self.tag_handler['sub'] = self.handler_simple_inline('^^')
        self.tag_handler['sup'] = self.handler_simple_inline(',,')
        self.tag_handler['code'] = self.handler_simple_inline('##')
        self.tag_handler['tt'] = self.handler_simple_inline('##')

        self.tag_handler['hr'] = lambda e,c: '\n----\n'
        self.tag_handler['br'] = lambda e,c: '\\\\'

    def handle_tag(self, elt, context=None):
        if context=="textonly":
            return self.handle_contents(elt, block=False, context='textonly')
        if context=="pre":
            return self.handle_contents(elt, block=False, context='pre')
        
        name = elt.name
        if name in self.tag_handler:
            # tags we can handle with the tandler dictionary
            return self.tag_handler[name](elt, context)

        #elif name == 'blockquote':
        #    return '\n> ' + self.handle_contents(elt, block=False)
        return '[unknown tag %s]' % (elt.name)


    def handle_element(self, elt, context=None):
        if elt is None:
            return ''
        elif type(elt) in [BeautifulSoup.Declaration, BeautifulSoup.Comment, BeautifulSoup.Declaration, BeautifulSoup.ProcessingInstruction]:
            return ''
        elif isinstance(elt, basestring):
            if type(elt) == BeautifulSoup.CData:
                s = BeautifulSoup.NavigableString.__str__(elt)
            else:
                s = unicode(elt)
            
            if context == 'pre':
                return s
            else:
                return self.wiki_escape(self.any_whitespace.sub(' ', s))
        elif type(elt) == BeautifulSoup.Tag:
            return self.handle_tag(elt, context=context)
        raise ValueError, str(type(elt))

    def from_soup(self, soup):
        """
        Convert a BeautifulSoup element to wikitext
        """
        segments = [self.handle_element(e) for e in soup.contents]
        res = ''.join(segments)
        res = self.blank_lines_re.sub('\n\n', res)
        return res.strip()
        
    def from_html(self, html):
        """
        Convert HTML source to wikitext
        """
        try:
            soup = BeautifulSoup.BeautifulSoup(html,
                   convertEntities=BeautifulSoup.BeautifulSoup.XHTML_ENTITIES)
        except:
            # any badness from BeautifulSoup becomes a ParseError
            raise self.ParseError, "Could not parse HTML"

        return self.from_soup(soup)

    def get_title(self, soup):
        """
        Get contents of the <title> element, if present
        """
        elt = soup.find('title')
        if elt:
            return self.handle_contents(elt, block=False, context="textonly")
        else:
            return None

    def from_html_full(self, html):
        """
        Convert HTML source to wikitext, returning wikitext and 
        """
        try:
            soup = BeautifulSoup.BeautifulSoup(html,
                   convertEntities=BeautifulSoup.BeautifulSoup.XHTML_ENTITIES)
        except:
            # any badness from BeautifulSoup becomes a ParseError
            raise self.ParseError, "Could not parse HTML"

        self.urls = set()
        title = self.get_title(soup)
        wiki = self.from_soup(soup)
        return wiki, title, self.urls

