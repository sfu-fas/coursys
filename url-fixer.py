#!/usr/bin/env python

import os, re

dot_ref_re = re.compile(r'(?P<quote>\'|\")(?P<app>\w+)\.views\.(?P<view>\w+)\1')


def intersting_file(f):
    return f.endswith('.html') or f.endswith('.py')


def fix_urls_py(fn):
    '''
    Add a name='foo' to each url pattern in this urls.py
    '''
    new_content = []
    with open(fn, 'r') as py:
        for line in py:
            line = line.rstrip() + '\n'
            newline = line
            m = dot_ref_re.search(line)

            # make sure every pattern has a name
            if m and 'name=' not in line:
                repl = '%s, name=%r' % (m.group(0), m.group('view'))
                newline = dot_ref_re.sub(repl, line)

            # undo the dotted-string style references
            if m:
                repl = '%s_views.%s' % (m.group('app'), m.group('view'))
                newline = dot_ref_re.sub(repl, newline)

            new_content.append(newline)


    with open(fn, 'w') as py:
        py.write(''.join(new_content))


for dirpath, dnames, fnames in os.walk("./"):
    for f in fnames:
        if intersting_file(f):
            if f == 'urls.py':
                fix_urls_py(os.path.join(dirpath, f))
