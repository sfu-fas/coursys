FROM debian:stable-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    logrotate cron procps \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Vancouver
COPY --chmod=0644 docker/files/logrotate-nginx.conf /etc/logrotate.d/nginx-coursys

# logrotate installs its own crontab, so just let cron fire it off as needed:
CMD cron -f -L 7
