#!/bin/bash

/usr/bin/kinit `cat /csrpt_auth/username`@AD.SFU.CA -k -t /csrpt_auth/adsfu.keytab
mv /tmp/krb5cc_${UID} /csrpt_auth/krb5cc
ln -s /csrpt_auth/krb5cc /tmp/krb5cc_${UID}

