# Dependency Updates

What in the system needs to be semi-regularly evaluated for being up to date (with security patches, etc)?
And how do we validate that things are okay after the update? 

## Python Pip

The Python packages mentioned in [requirements.txt](../requirements.txt) should be periodically brought up to date.
The easiest thing seems to be scanning requirements and checking current versions in (PyPI)(https://pypi.org/). Also consider:
```shell
pip list --outdated
```

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

To exercise a more-production-like environment, the tests should run in containers as well.
```shell
ln -sf compose-proddev.yml compose.yml
docker compose build
docker compose run manage test
```

### Django

Of course, Django is the most critical dependency, and often itself a sub-dependency of other packages we use. Likely
it's easiest to update *everything else* and then look at the Django version.

Have a look at the Django release notes on major releases (x.0.0 or maybe x.y.0) for:
* any "backwards incompatible changes" for anything we actually use,
* supported Python versions (vs what we have in production),
* supported database version (vs what we have in production).

Typically, I start by just getting the tests to pass. There are often minor changes: obscure methods that got renamed or sketchy things we did that are now caught as errors and should be tidied up.

It's then time to check things in proddev deployment (see `DOCKER_PRODDEV.md`). Make sure Celery tasks run, etc.


### Celery

In the past, Celery updates have been annoying, but that has been easier in recent versions.

It's still necessary to test: get yourself into proddev mode and make sure tasks move around as expected.


### Production-Only Requirements

There are a couple of things that by necessity only happen in production.
* CAS authentication
* Reporting database/CSRPT access (which passes through the pyodbc module).

Updates for these libraries are hard to test. At worst, may be necessary to delicately test in production. That may be:
* create a separate branch
* check it out in production. Build. Hope production containers don't restart any time soon.
* run the `manage` or `admin` containers manually to poke around.
* check out master again. Build.


## Static Files, NPM

JavaScript dependencies are in `package.json`: versions can be bumped as necessary.
```shell
npm install
```
The page of frontend checks should give a quick view on the various libraries working or not: http://localhost:8000/sysadmin/frontend-check

Of course, checking the behaviour *in situ* use is a good idea too.

Be sure to add changes to both `package.json` and `package-lock.json`: the containers do a `npm ci` which uses the exact versions from the lock file.


## Docker Images

The final source of stale code: `compose-template.yml` and the Dockerfiles in `docker/`. Have a look at the `FROM` lines in the Dockerfiles and the
versions of images referenced in `compose-template.yml`. After updating the template:
```shell
./manage.py build_compose_yml ALL
```
Inspect the system running in Docker and make sure tests past, functionality we use works as best you can see, etc.

In general, there's no guarantee that the on-disk formats will be compatible across versions. Perhaps check data compatibility and plan an upgrade/migration in production. The persistent data stored by Docker services isn't critical:

* memcached: doesn't store persistent data. Update freely.
* rabbitmq: stores pending Celery tasks. If you can make sure the Celery queue is empty, then any stored data is unimportant. See the "`make drain-tasks`" recipe.
* elasticsearch: stores the full-text indexes. Needed, but at worst, `docker compose run manage update_index_task --full-rebuild` will restore them fully.
* other containers: no persistent state relevant to version updates.


## Main Database

Get some tech help.

Basically: stop the world (`make 503`), do a `mysqldump` on the old DB server and restore to the new DB server. Make sure the system is looking at the new server (i.e. update `courses/secrets.py` and `make new-code-lite`).

See also `PRODUCTION_SETUP.md`.