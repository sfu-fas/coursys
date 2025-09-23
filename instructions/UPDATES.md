# Dependency Updates

What in the system needs to be semi-regularly evaluated for being up to date (with security patches, etc)?
And how do we validate that things are okay after the update? 

## Python Pip

The Python packages mentioned in [requirements.txt](../requirements.txt) should be periodically brought up to date.
The easiest thing seems to be scanning requirements and checking current versions in (PyPI)(https://pypi.org/).

Generally, I update a few packages at a time (not Django and Celery, which are discussed below) and test to make sure basic things work with them:
```shell
pip install -r requirements.txt
./manage.py migrate  # maybe?
./manage.py test
python3 -Wall ./manage.py test  # for all warnings, which are sometimes informative
```

For packages with specific effects (e.g. reportlab for PDF generation, haystack for search), a quick manual check that they are working as expected may be wise.

If anything is found that is **not** caught by tests, it's strongly encouraged to add a tests that exercises that package a little more.

There are some tests of library behaviour in `coredata.tests.DependencyTest`: if any libraries behave badly on update, it might be wise to add some tests for the kinds of things we do with them here, in the hopes of failing-fast in the future.


### Django

Of course, Django is the most critical dependency, and often itself a sub-dependency of other packages we use. Likely
it's easiest to update *everything else* and then look at the Django version.

Have a look at the Django release notes on major releases (x.0.0 or maybe x.y.0) for:
* any "backwards incompatible changes" for anything we actually use,
* supported Python versions (vs what we have in production),
* supported database version (vs what we have in production).

Typically, I start by just getting the tests to pass. There are often minor changes: obscure methods that got renamed or sketchy things we did that are now caught as errors and should be tidied up.

It's then time to check things in proddev deployment (see DOCKER_PRODDEV.md or VM_PRODDEV.md). Make sure Celery tasks run, etc.


### Celery

In the past, Celery updates have been annoying, but that has been easier in recent versions.

It's still necessary to test: get yourself into proddev mode and make sure tasks move around as expected.


### Production-Only Requirements

There are a couple of things that by necessity only happen in production.
* CAS authentication
* Reporting database/CSRPT access (which passes through the pyodbc module).

Updates for these libraries are hard to test.


## Static Files, NPM

JavaScript dependencies are in `package.json`: versions can be bumped as necessary.
```shell
npm install
./manage.py collectstatic  # if you need it
```
The page of frontend checks should give a quick view on the various libraries working or not: http://localhost:8000/frontend-check

Of course, checking the behaviour *in situ* use is a good idea too.



## Docker Images

The final source of stale code: `docker-compose.yml`. The docker containers can be run in a proddev mode. See `DOCKER_PRODDEV.md`.

Since they store persistent data (in `/data/`), and there's no guarantee that the on-disk format will be compatible across versions, updates may lose that data but there's nothing critical in them:

* memcached: doesn't store persistent data. Update freely.
* rabbitmq: stores messages in-queue (i.e. pending Celery tasks). If you can make sure the Celery queue is empty, then any stored data is unimportant.
* elasticsearch: stores the full-text indexes. Needed, but at worst, `./manage.py rebuild_index` will restore them fully.

Procedure to update containers needs better docs.


## Main Database

Get some tech help.

Basically: stop the world (`make 503`), do a `mysqldump` on the old DB server and restore to the new DB server. Make sure the system is looking at the new server (i.e. update `courses/secrets.py` and `make new-code-lite`).