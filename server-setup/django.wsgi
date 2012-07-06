#!/usr/bin/env python

# sample FastCGI script to get things running under Apache. Accompanies Apache config like:
"""
NameVirtualHost *:81
Listen 81
<VirtualHost *:81>
ServerAdmin ggbaker@sfu.ca
ServerName lefty.cmpt.sfu.ca
DocumentRoot /home/fastcgi/demo/fcgi
WSGIScriptAlias / /home/fastcgi/demo/fcgi/django.wsgi
WSGIDaemonProcess coursysdemo user=fastcgi
ErrorLog /var/log/apache2/error.log
Alias /media /home/fastcgi/demo/courses/media
</VirtualHost> 
"""

# cribbed from http://code.google.com/p/modwsgi/wiki/VirtualEnvironments

ALLDIRS = ['/home/fastcgi/demo/lib/python2.7/site-packages']

import os, sys, site

# Remember original sys.path.
prev_sys_path = list(sys.path) 

# Add each new site-packages directory.
for directory in ALLDIRS:
  site.addsitedir(directory)

# Reorder sys.path so new directories at the front.
new_sys_path = [] 
for item in list(sys.path): 
    if item not in prev_sys_path: 
        new_sys_path.append(item) 
        sys.path.remove(item) 
sys.path[:0] = new_sys_path 


# from my CMPT 470 Django instructions

# make sure app's modules can be found
sys.path.append('/home/fastcgi/demo')
sys.path.append('/home/fastcgi/demo/courses')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Switch to the directory of your project. (Optional.)
os.chdir("/home/fastcgi/demo/courses")

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
