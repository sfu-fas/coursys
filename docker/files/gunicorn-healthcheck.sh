#!/bin/sh

set -e

curl --fail -H "Host: ${HEALTHCHECK_HOSTNAME}" http://localhost:8000/healthcheck