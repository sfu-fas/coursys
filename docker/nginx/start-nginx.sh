#!/bin/sh

# Ensure *some* nginx-backends.conf exists in a sane state 
[ -f /dynamic_config/nginx-backends.conf ] || cp /etc/nginx/backends-default.conf /dynamic_config/nginx-backends.conf
chown ${UID} /dynamic_config/nginx-backends.conf
chmod 0644 /dynamic_config/nginx-backends.conf

exec nginx -g "daemon off;"