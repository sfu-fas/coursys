FROM debian:stable-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    logrotate procps \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Vancouver
COPY --chmod=0644 docker/files/logrotate-nginx.conf /etc/logrotate.d/nginx-coursys
COPY --chmod=0755 docker/files/logrotate.sh /logrotate.sh

CMD ["/logrotate.sh"]