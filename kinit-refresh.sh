#!/bin/sh

/usr/bin/kinit `cat /csrpt_auth/username`@AD.SFU.CA -k -t /csrpt_auth/adsfu.keytab

