#!/bin/bash

set -e

# This is a shim to set the ELASTIC_PASSWORD environment variable if necessary from a 
# secret file, ELASTIC_PASSWORD_SECRET
if [ ! -z ${ELASTIC_PASSWORD_SECRET+x} -a -f ${ELASTIC_PASSWORD_SECRET} ] ; then \
    echo "setting ELASTIC_PASSWORD"; \
    export ELASTIC_PASSWORD=$(cat ${ELASTIC_PASSWORD_SECRET}); \
fi

exec /usr/local/bin/docker-entrypoint.sh