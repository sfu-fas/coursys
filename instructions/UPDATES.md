# Dependency Updates

What in the system needs to be semi-regularly evaluated for being up to date (with security patches, etc)?
And how do we validate that things are okay after the update? 

## Python Pip



### Celery


## NPM


Be sure to purge your `static/`, `./manage.py collectstatic` and test with `COMPRESS_ENABLED=True`.

TODO frontend-check should be compressed and in a test

## Docker Images
