#!/bin/sh

# --logfile=/celery_logs/${QUEUE}.log
exec celery -A courses worker --loglevel INFO  \
    --queues ${QUEUE} --hostname ${QUEUE} --concurrency ${CONCURRENCY}
