FROM nginx:1

COPY docker/nginx-common.conf /etc/nginx/common.conf
COPY docker/nginx-default.conf /etc/nginx/conf.d/default.conf
