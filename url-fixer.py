#!/usr/bin/env python

import os, re, sys

from django.core.wsgi import get_wsgi_application
sys.path.append('.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
application = get_wsgi_application()

from django.core.urlresolvers import get_resolver, get_callable
resolver = get_resolver()

dot_ref_re = re.compile(r'(?P<quote>\'|\")(?P<dotted>(?P<app>\w+)\.views\.(?P<view>\w+))\1')
function_reverse_re = re.compile(r'reverse\((?P<funcname>\w+)')
no_namespace_tag_re = re.compile(r'{\%\s*url[^:]{15,}')

from api.views import oauth_authorize, oauth_callback
initial_view_names = {
    oauth_authorize: 'api.views.oauth_authorize',
    oauth_callback: 'api.views.oauth_callback',
}

def intersting_file(f):
    return 'oldcode' not in f and (f.endswith('.html') or f.endswith('.py'))


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


def catalogue_resolver(resolver, ns=()):
    #index_full = get_callable('dashboard:index_full')
    view_names = initial_view_names
    resolver._populate()
    for fn in list(resolver.reverse_dict.keys()):
        if isinstance(fn, str) or fn.__name__ in ['RedirectView']:
            continue
        new_name = ':'.join(ns + (fn.__name__,))
        view_names[fn] = new_name

    for n,v in list(resolver.namespace_dict.values()):
        this_ns = ns + (v.namespace,)
        #print this_ns, v
        vns = catalogue_resolver(v, ns=this_ns)
        view_names.update(vns)

    return view_names


def fix_references(fn, view_names):
    new_content = []
    with open(fn, 'r') as code:
        for line in code:
            m = dot_ref_re.search(line)
            if m:
                dotted = m.group('dotted')
                viewfunc = get_callable(dotted)
                newline = line.replace(dotted, view_names[viewfunc])
            else:
                newline = line
            new_content.append(newline)

            m = function_reverse_re.search(line)
            if m:
                print("function reference reverse() in ", fn)

            m = no_namespace_tag_re.search(line)
            if m:
                print("no namespace on {% url %} in ", fn)

    with open(fn, 'w') as py:
        py.write(''.join(new_content))



def main():
    view_names = catalogue_resolver(resolver)
    for dirpath, dnames, fnames in os.walk("./"):
        for f in fnames:
            fullpath = os.path.join(dirpath, f)
            if intersting_file(fullpath):
                if f == 'urls.py':
                    fix_urls_py(fullpath)
                else:
                    fix_references(fullpath, view_names)

main()