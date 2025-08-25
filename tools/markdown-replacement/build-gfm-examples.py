import urllib.request
import bs4

URL = 'https://github.github.com/gfm/'
FILENAME = 'gfm.html'


def extract_text(elt):
    if isinstance(elt, bs4.element.Tag):
        return ''.join(extract_text(c) for c in elt.children)
    elif isinstance(elt, bs4.element.NavigableString):
        return str(elt).replace('→', '\t')
    else:
        raise ValueError(type(elt))


try:
    html = open(FILENAME, 'rt', encoding='utf-8').read()
except FileNotFoundError:
    html = urllib.request.urlopen(URL).read().decode('utf-8')
    open(FILENAME, 'wt', encoding='utf-8').write(html)
    

soup = bs4.BeautifulSoup(html, "html5lib")
for pre in soup.find_all('pre'):
    for md in pre.find_all('code', class_='language-markdown'):
        md_code = extract_text(md)
        print(md_code)
        print('\n\n')
