FROM nginx:1

ARG SERVE_HOSTS
ARG REDIRECT_HOSTS
ARG CANONICAL_NAME
ARG USER_PROTOCOL
ARG USER_PORT
ENV SERVE_HOSTS=${SERVE_HOSTS}
ENV REDIRECT_HOSTS=${REDIRECT_HOSTS}
ENV CANONICAL_NAME=${CANONICAL_NAME}
ENV USER_PROTOCOL=${USER_PROTOCOL}
ENV USER_PORT=${USER_PORT}
ENV TZ=America/Vancouver

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
  CMD curl --fail http://localhost:80/static/icons/favicon.ico?healthcheck || exit 1

COPY docker/nginx/common.conf /etc/nginx/common.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/nginx/serve-host.conf /etc/nginx/
COPY docker/nginx/redirect-host.conf /etc/nginx/
COPY docker/nginx/default-host.conf /etc/nginx/
COPY docker/nginx/configure-hosts.sh /etc/nginx/

# The configure-hosts.sh script is responsible for appending server{} blocks to the nginx
# config for whatever hostnames we're dealing with, either by serving directly, or forwarding to
# the canonical name.
RUN /etc/nginx/configure-hosts.sh

# View the resulting config:
# docker compose run nginx cat /etc/nginx/conf.d/default.conf
