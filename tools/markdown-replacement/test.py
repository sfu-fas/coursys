import difflib
import io
import os
import subprocess

import mistletoe
import mistune
import cmarkgfm
import pycmarkgfm


def commonmark(text: str) -> str:
    with subprocess.Popen(['ruby', 'cm.rb'], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        proc.stdin.write(text.encode('utf-8'))
        proc.stdin.close()
        res = proc.stdout.read()
    return res.decode('utf-8')


def mistletoe_md(text: str) -> str:
    renderer = mistletoe.HtmlRenderer(process_html_tokens=True)
    return renderer.render(mistletoe.Document(io.StringIO(text)))


def pycmarkgfm_md(text: str) -> str:
    options = pycmarkgfm.options.github_pre_lang
    extensions = ['autolink', 'strikethrough', 'table', 'tagfilter']
    with pycmarkgfm.parse_markdown(text, options=options, extensions=extensions) as document:
        return document.to_html()


def cmarkgfm_md(text: str) -> str:
    options = cmarkgfm.Options.CMARK_OPT_GITHUB_PRE_LANG
    extensions = ['table', 'autolink', 'tagfilter', 'strikethrough']
    return cmarkgfm.markdown_to_html_with_extensions(text, options=options, extensions=extensions)


converters = {
    #'mistletoe': mistletoe_md,
    #'mistune': mistune.html,
    'pycmarkgfm': pycmarkgfm_md,
    'cmarkgfm': cmarkgfm_md,
}


def run_test(infile: str):
    text = open(infile, 'rt', encoding='utf-8').read()
    reference = commonmark(text).split('\n')
    #print(reference)
    for name, func in converters.items():
        print(f'--- {name} ---')
        html = func(text).split('\n')
        diff = difflib.unified_diff(reference, html, fromfile='commonmark', tofile=name)
        for l in diff:
            print(l)


for fn in os.listdir('tests'):
    print(f'=== {fn} ===')
    run_test(f'tests/{fn}')
