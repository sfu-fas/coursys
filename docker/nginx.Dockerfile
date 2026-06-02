FROM nginx:1

ARG SERVE_HOSTS="coursys.sfu.ca fasit.sfu.ca"
ARG FORWARD_HOSTS="courses.cs.sfu.ca"
ARG CANONICAL_NAME="coursys.sfu.ca"

ENV SERVE_HOSTS=${SERVE_HOSTS}
ENV FORWARD_HOSTS=${FORWARD_HOSTS}
ENV CANONICAL_NAME=${CANONICAL_NAME}

COPY docker/nginx-common.conf /etc/nginx/common.conf
COPY docker/nginx-default.conf /etc/nginx/conf.d/default.conf
COPY docker/nginx-serve-host.conf /etc/nginx/
COPY docker/nginx-forward-host.conf /etc/nginx/
COPY docker/nginx-configure-hosts.sh /etc/nginx/

# The nginx-configure-hosts.sh script is responsible for appending server{} blocks to the nginx
# config for whatever hostnames we're dealing with, either by serving directly, or forwarding to
# the canonical name.
RUN /etc/nginx/nginx-configure-hosts.sh
