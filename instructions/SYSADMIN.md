# CourSys System Administration Notes

This document collects some of the things needed to work with CourSys in full production mode, as it is deployed.


## Deployment Basics

See `PRODUCTION_SETUP.md` for details on how the system needs to be/is deployed in production.

tl;dr `docker compose` with the `compose-production.yml` Compose file.


## What's Running

The services running in production are either docker containers (configured in `docker-compose.yml`) or systemd services.

* Nginx: the frontend web server.
* Gunicorn (container "app"): the backend server actually running CourSys. (Proxied by nginx to the outside world.)
* Celery workers (5 of them, one for each queue): a task queue running asynchronous and periodic tasks (anything in `*/tasks.py`).
* Celerybeat: a service responsible dispatching Celery periodic tasks.
* RabbitMQ: message queue used by Celery.
* ElasticSearch: used for the site search and autocomplete (through the Django haystack library).
* Memcached: temporary caching (through the Django caching framework).
* Logrotate: a little container rotating the nginx logs.

See `arch.png` for that in diagram form. Or `dockerfiles.png` for an overview of how the containers get built.

### Not Running

There are two containers that generally aren't running that can be used by admins.

The `manage` container can be used to conveniently run Django `manage.py` commands:
```shell
docker compose run manage shell
```

And `admin` can be used to run shell commands.
```shell
docker compose run manage ls -l /
docker compose run manage bash
```


## What's Stored

There are only two places where important persistent data is stored:

* The database (MariaDB managed by SFU IT Services and CSTS), i.e. `DATABASES['default']` from settings.py.
* The files that have been uploaded, i.e. `SUBMISSION_PATH` from settings.py, mounted into containers at `/submitted_files`.

The search indices in ElasticSearch are managed by that Docker container (volume from `/data/elasticsearch*`), but those can always be recreated with a `manage.py rebuild_index`.

In theory the RabbitMQ messages can encode tasks in-flight that could lose data if destroyed: as long as no tasks are in motion then nothing important is in RabbitMQ. The easiest way to ensure this is probably `make 503; docker compose up -d celery-*` and make sure any pending tasks complete.

Memcached stores only ephemeral cache and can be freely purged.


## System Checks

The system knows how to check its deployment environment quite thoroughly. These checks can be triggered with:
```shell
docker compose run manage check_things
```
Or visit https://coursys.sfu.ca/sysadmin/panel (as an account with system admin role) and check the "Deployment Checks" tab.

There is also a much more minimal check done, where any failures would prevent the Django-based containers from starting:
```shell
docker compose run manage check
```


## CSRPT Auth

The production server must have [kerberos authentication](https://sfu.teamdynamix.com/TDClient/255/ITServices/KB/ArticleDet?ID=3932) done by someone with Reporting Database access.

See `REPORTING_DATA.md` for details on how this happens.


## Common Tasks

The `Makefile` in the repository root is basically a collection of useful scripts.

They all assume (1) the user running `make` can `sudo`; (2) the `coursys` user *cannot* `sudo`. So, if new code needs to be deployed, with a real-person account:
```shell
cd /coursys
make pull
make new-code
```

* `make pull`: do a `git pull`, preserving the runlist file that likely contains local modifications. 
* `make new-code`: rebuild containers and restart everything that's necessary when deploying modified code.
* `make new-code-pull`: like `new-code` but pulls new base images for the containers.
* `make migrate-safe`: a paranoid database migration: perform a database backup, then Django migration, then another database backup.
* `make 503`: put the whole system into "503 unavailable" mode (and stop celery tasks, which might also be doing things) so nothing is happening in the database or filesystem.
* `make rm503`: undo `make 503`


##  Logs

Most logs are left to Docker, so you can check what has been happening with Docker's log tools:
```shell
docker compose logs app
```

The outliers is Nginx which has logs stored outside of Docker in `/data/nginx_logs`, and the Celery workers in `/data/celery_logs`.


## Deploying code

Almost all the time, the procedure is:

1. Accept a pull request into the master branch, or push into master.
2. Log on to the production server.
3. Get the code: `make pull`.
4. Get that code running: `make new-code`. This reloads/restarts the gunicorn and celery containers.
4. Make sure our deployment checks pass:  System Administration -> View Admin Panel -> Deployment Checks
5. Maybe also make sure emails are going through: the admin panel Email Check tab.

### With Maximum Paranoia

If you're worried, it may be worth putting the server into "503 unavailable" mode to make sure nothing happens in an inconsistent state.
It's also possible to build the containers before actually trying to deploy them.

```shell
make 503
make pull
make migrate-safe  # takes database snapshots before and after migration
make build
docker compose manage check_things
make new-code
make rm503
```


## Server Messages

The system can display all-user status messages either on the top index page (`SERVER_MESSAGE_INDEX`) or on every page (`SERVER_MESSAGE`).

These can be controlled in the container images' `courses/localsettings.py` (copied from `courses/docker-localsettings-production.py` for a production deployment). Changing these files would require a build and rollout.

If present, they are also read from the `dynamic_config` volume: `/data/dynamic_config/server_message_index.html` and `/data/dynamic_config/server_message.html` on the server. You can create/edit/delete those files (with some reasonably-valid HTML) and tell the gunicorn process to gracefully restart its workers:
```shell
docker compose kill -s SIGHUP app  # gunicorn 
```


## In Case of Problems

The *hope* is that we have enough system checks that if the system comes up, it comes up correctly. Running `make new-code` uses docker-rollout, which checks the health status of the main Django container (`app`) and waits to bring down the old containers until the new ones are healthy. If that fails, it also leaves the various Celery containers as-is. In theory, that should prevent broken deployments from taking over.

If there's any confusion, it might be informative to run the Django container in various ways to see what's going on. Perhaps one of:
```shell
docker compose run app ./manage.py shell
docker compose run app ./manage.py dbshell
docker compose run app ./manage.py check_things
docker compose run app bash
```

Just running any `manage` command will often trigger whatever error is happening, in a more helpful environment.

A database dump is done every few hours in production into `/filestore/prod/db_backup/`. In a worst-case scenario, these can be examined for changes in the database and/or information on what has been happening.


## An Emergency Revert

In the case that something has somehow been merged and deployed, but is failing, it may be necessary to do a quick revert to the previously-good code state.

First, find the desired git commit. That could be done in the github, or in the local git log:
```shell
git log
```

That should reveal a commit that you'd like to target, identified by a long hex string. Then you can check out that moment and get things started again.
```shell
sudo -u coursys git checkout 1234567890123456789abcdefabcdef
make new-code
```

Investigate. Fix master.
```shell
sudo -u coursys git checkout master
make pull
make new-code
```