#!/bin/sh

QUEUE=$1
CONCURRENCY=$2

# --logfile=/celery_logs/${QUEUE}.log
celery -A courses worker --loglevel INFO  \
    --queues ${QUEUE} --hostname ${QUEUE} --concurrency ${CONCURRENCY}
