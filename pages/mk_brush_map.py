#!/usr/bin/env python

src_dir = "media/syntaxhighlighter/scripts/"

import sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

import re
from pages.models import brushre

fn_re = re.compile(r"^\w+\.js$")
line_re = re.compile(r"^\s*Brush.aliases\s*=\s*\[(.*)\];\s*$")
sep_re = re.compile(r",\s*")
brushstr_re = re.compile("\'(" + brushre + ")\'")

brush_code = {}

for fn in os.listdir(src_dir):
    if not fn_re.match(fn):
        continue

    for line in open(os.path.join(src_dir, fn)):
        m = line_re.match(line)
        if not m:
            continue

        aliaslist = m.group(1)
        aliases = sep_re.split(aliaslist)
        for astr in aliases:
            bm = brushstr_re.match(astr)
            a = bm.group(1)
            brush_code[a] = fn

print 'brush_code = ' + repr(brush_code)


