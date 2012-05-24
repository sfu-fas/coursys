#!/bin/sh

touch db.sqlite \
  && rm db.sqlite \
  && echo "no" | python manage.py syncdb \
  && python manage.py migrate \
  && python manage.py loaddata test_data
