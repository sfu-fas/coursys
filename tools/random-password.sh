#!/bin/sh

# generate a reasonable random password we could use for internal services

tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 10
echo