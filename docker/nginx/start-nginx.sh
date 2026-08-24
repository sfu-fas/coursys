#!/bin/sh

[ -f /dynamic_config/nginx-backends.conf ] || cp /etc/nginx/backends-default.conf /dynamic_config/nginx-backends.conf
chown ${UID} /dynamic_config/nginx-backends.conf

exec nginx -g "daemon off;"