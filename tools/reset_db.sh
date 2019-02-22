#!/bin/sh

touch db.sqlite \
  && rm db.sqlite \
  && python manage.py syncdb \
  && python manage.py loaddata fixtures/*.json \
  && python manage.py update_index
