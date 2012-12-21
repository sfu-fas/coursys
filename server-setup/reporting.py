#!/usr/bin/env python

# Open up a connection to the reporting DB and damn-well keep it open.
# Called in a screen session as part of reportingdb.sh.

import os, sys, time
import pexpect

user = os.environ['USER']
pw = os.environ['PW']

while True:
    child = pexpect.spawn('ssh',  ['-L', '127.0.0.1:50000:hutch.ais.sfu.ca:50000', '-l', user, '-N', 'pf.sfu.ca'])
    child.logfile_read = sys.stdout
    child.expect('[pP]assword: ')
    child.sendline(pw)
    print
    child.wait()
    time.sleep(60) # pause to avoid being overly agressive in case of failure

