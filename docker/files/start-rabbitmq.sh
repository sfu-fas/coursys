#!/bin/bash

set -e

# This is a shim to set the RABBITMQ_DEFAULT_PASS environment variable if necessary, since RABBITMQ_DEFAULT_PASS_FILE is no longer supported.
# Leaves RABBITMQ_DEFAULT_PASS unchanged if the secret file doesn't exist.
if [ ! -z ${RABBITMQ_DEFAULT_PASS_SECRET+x} -a -f ${RABBITMQ_DEFAULT_PASS_SECRET} ] ; then \
    echo "setting RABBITMQ_DEFAULT_PASS"; \
    export RABBITMQ_DEFAULT_PASS=$(cat ${RABBITMQ_DEFAULT_PASS_SECRET}); \
fi

exec rabbitmq-server