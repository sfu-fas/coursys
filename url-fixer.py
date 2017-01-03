#!/usr/bin/env python

import os, re

dot_ref_re = re.compile(r'(?P<quote>\'|\")(?P<app>\w+)\.views\.(?P<view>\w+)\1')


def intersting_file(f):
    return f.endswith('.html') or f.endswith('.py')


def fix_urls_py(fn):
    new_content = []
    with open(fn, 'r') as py:
        for line in py:
            line = line.rstrip() + '\n'
            m = dot_ref_re.search(line)
            if m:
                repl = "%s, name=%r" % (m.group(0), m.group('view'))
                new_content.append(dot_ref_re.sub(repl, line))
            else:
                new_content.append(line)

    with open(fn, 'w') as py:
        py.write(''.join(new_content))


for dirpath, dnames, fnames in os.walk("./"):
    for f in fnames:
        if intersting_file(f):
            #print f
            if f == 'urls.py':
                fix_urls_py(os.path.join(dirpath, f))