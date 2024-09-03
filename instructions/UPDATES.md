# Dependency Updates

What in the system needs to be semi-regularly evaluated for being up to date (with security patches, etc)?
And how do we validate that things are okay after the update? 

## Python Pip

The Python packages mentioned in [requirements.txt](../requirements.txt) should be periodically brought up to date.
The easiest thing seems to be scanning requirements and checking current versions in (PyPI)(https://pypi.org/).

Generally, I update a few packages at a time (not Django and Celery, which are discussed below) and test to make sure
basic things work with them:
```shell
pip install -r requirements.txt
./manage.py migrate  # maybe?
./manage.py test
```

For packages with specific effects (e.g. reportlab for PDF generation, haystack for search), a quick manual check that
they are working as expected may be wise.

If anything is found that is **not** caught by tests, it's strongly encouraged to add a tests that exercises that
package a little more.



### Django

Of course, Django is the most critical dependency, and often itself a sub-dependency of other packages we use. Likely
it's easiest to update *everything else* and then look at the Django version.

Have a look at the Django release notes for:
* any incompatible changes (which are typically explicitly listed) for anything we actually use,
* supported Python versions (vs what we have in production),
* supported database version (vs what we have in production).

(e.g. )


### Celery


## NPM


Be sure to purge your `static/`, `./manage.py collectstatic` and test with `COMPRESS_ENABLED=True`.

TODO frontend-check should be compressed and in a test

## Docker Images
