#!/bin/bash

# running cron in docker was just too annoying, and logrotate tracks its own state anyway so can run as often as we want.
# consider pinning the time: https://unix.stackexchange.com/a/94548

while true; do \
    date; \
    echo "Running logrotate"; \
    /usr/sbin/logrotate /etc/logrotate.conf; \
    sleep 300;
done
  
