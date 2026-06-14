#!/bin/sh

set -e

# check that we're in a sane environment before even trying to start
python /coursys/manage.py check

exec celery -A courses worker --loglevel INFO  \
    --queues ${QUEUE} --hostname ${QUEUE} --concurrency ${CONCURRENCY}
