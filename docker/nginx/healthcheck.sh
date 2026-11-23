#!/bin/sh

set -e

# check that static files are being served
curl --fail http://localhost:80/static/icons/favicon.ico?healthcheck

# and that at least one of othe backends resolve
getent hosts app-a || getent hosts app-b
