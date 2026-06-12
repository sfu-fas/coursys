#!/bin/sh

set -e

# check that we're in a sane environment before even trying to start
python /coursys/manage.py sanity_check

exec gunicorn --workers=5 --worker-class=sync --max-requests=100 --max-requests-jitter=10 --bind=0.0.0.0:8000 courses.wsgi:application
