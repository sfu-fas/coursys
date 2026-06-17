# Based on https://github.com/samuelru/logrotate
# ... but recreated specific to our use, removing a dependency.
# Container must be deployed with "--pid=host" so the "reopen log files" signal can be sent.

FROM alpine:latest

RUN apk add --no-cache \
    logrotate \
    tzdata \
    bash \
    coreutils \
    findutils \
    grep

ENV TZ=America/Vancouver
# volume for the logrotate status file: this will let it survive rebuild, but no great loss if it disappears.
VOLUME /status

COPY --chmod=0644 docker/files/logrotate-nginx.conf /etc/logrotate.d/nginx-coursys
RUN echo "0 5 * * * /usr/sbin/logrotate -v --state /status/logrotate.status /etc/logrotate.d/nginx-coursys" > /etc/crontabs/root

CMD ["crond", "-f", "-d", "8"]