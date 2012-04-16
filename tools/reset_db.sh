#!/bin/sh

touch db.sqlite \
  && rm db.sqlite \
  && echo "no" | ./manage.py syncdb \
  && ./manage.py migrate \
  && ./manage.py loaddata test_data
