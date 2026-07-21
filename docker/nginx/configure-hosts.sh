#!/bin/bash

set -e

OUTFILE=/etc/nginx/conf.d/default.conf
cd /etc/nginx

# Treat the .conf fragments as an ad-hoc template language with the few replacements we have...
do_replacements_and_append () {
    INFILE=$1
    HOST=$2
    echo -e "\n" >> ${OUTFILE}
    cat ${INFILE} \
        | sed "s/DOMAIN_NAME/"${HOST}"/g" \
        | sed "s/CANONICAL_NAME/"${CANONICAL_NAME}"/g" \
        | sed "s/USER_PROTOCOL/"${USER_PROTOCOL}"/g" \
        | sed "s/USER_PORT/"${USER_PORT}"/g" \
        >> ${OUTFILE}
    echo -e "\n" >> ${OUTFILE}
}

for HOST in ${SERVE_HOSTS}
do
  do_replacements_and_append serve-host.conf ${HOST}
done

for HOST in ${REDIRECT_HOSTS}
do
  do_replacements_and_append redirect-host.conf ${HOST}
done

do_replacements_and_append default-host.conf x
