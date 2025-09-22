# CourSys System Administration Notes

This document collects some of the things needed to work with CourSys in full production mode, as it is deployed.


## Deployment Basics

The system is deployed in `/coursys/` and runs as the user `coursys`.
That user shouldn't be able to log into the system directly: a real person must SSH-in, and `sudo` from there.

Deployment happens in two phases:
1. A basic VM with a basic Ubuntu configuration. This has been done by the CS tech staff, using their recipes. In particular, this should include firewall setup (ports 80, 443 open, and SSH minimally-open).
2. The CourSys chef deployment recipe. That is `deploy/cookbooks/coursys/recipes/default.rb` in this repo.


## What's Running

The services running in production are either docker containers (configured in `docker-compose.yml`) or systemd services.

* Nginx (systemd service): the frontend web server.
* Docker (systemd service): required to have the docker-based services running.
* Gunicorn (systemd service): the backend server actually running CourSys. (Proxied by nginx to the outside world.)
* Celery (systemd service): a task queue running asynchronous and periodic tasks (anything in `*/tasks.py`).
* Celerybeat (systemd service): a service responsible dispatching Celery periodic tasks.
* RabbitMQ (docker container): message queue used by Celery.
* ElasticSearch (docker container): used for the site search and autocomplete (through the Django haystack library).
* Memcached (docker container): temporary caching (through the Django caching framework). May be safely restarted any time.
* Ruby Markup microservice (docker container): a microservice to let us user the (Ruby-only) library for github-flavoured markdown.

See `arch.png` for that in diagram form.

## What's Stored

There are only two places where important persistent data is stored:

* The database (MariaDB managed by SFU IT Services and CSTS), i.e. `DATABASES['default']` from settings.py.
* The files that have been uploaded, i.e. `SUBMISSION_PATH` from settings.py

The search indices in ElasticSearch are managed by that Docker container (it has a volume for the database directory), but those can always be recreated with a `manage.py rebuild_index`.

In theory the RabbitMQ messages can encode tasks in-flight that could lose data if lost: as long as no tasks are in motion then nothing important is in RabbitMQ. The easiest way to ensure this is probably `make 503; service start celery` and make sure any pending tasks complete.

Memcached stores only ephemeral cache and can be freely purged.s


## System Checks

The system knows how to check its deployment environment quite thoroughly. These checks can be triggered with one of these commands (depending on currently-active user):
```shell
make manage ARGS=check_things
python3 manage.py check_things
```
Or visit https://coursys.sfu.ca/sysadmin/panel (as an account with system admin role) and check the "Deployment Checks" tab.


## CSRPT Auth

The production server must have [kerberos authentication](https://sfu.teamdynamix.com/TDClient/255/ITServices/KB/ArticleDet?ID=3932) done by someone with Reporting Database access. On the server, that can be done like this:
```shell
sudo su -l coursys
/coursys/kinit.sh
```
Enter your username and password when prompted. This creates authentication details in `~/kerberos` that are used by a cron job to regularly refresh the ticket.


## Common Tasks

The `Makefile` in the repository root is basically a collection of useful scripts.

They all assume (1) the user running `make` can `sudo`; (2) the `coursys` user *cannot* `sudo`. So, if new code needs to be deployed, with a real-person account:
```shell
cd /coursys
make pull
make new-code
```

* `make production-chef`: run the chef recipe. Should always be safe, if our recipe is correct.
* `make pull`: do a `git pull`, preserving the runlist file that likely contains local modifications. 
* `make new-code`: restart everything that's necessary when deploying modified code.
* `make rebuild`: make sure things are up-to-date: apt upgrade, install dependencies (Python libs), `make new-code`. 
* `make rebuild-hardcore`: try very hard to do to get the system into a coherent state with the system in "503 unavailable" mode when critical: update docker images, restart everything
* `make chef`: run the Chef recipe that configures the system (the only thing not done by rebuild-hardcore).
* `make 503`: put the whole system into "503 unavailable" mode (and stop celery tasks, which might also be doing things) so nothing is happening in the database or filesystem.
* `make rm503`: undo `make 503`
* `make restart-all`: a more serious restart than should generally be necessary: the docker containers and all CourSys-related services.


## Services and Logs

### Nginx

Nginx is installed as an Ubuntu package.

The main NGINX access logs are `/opt/nginx-logs/coursys.sfu.ca-http.access.log` and error logs at `/opt/nginx-logs/coursys.sfu.ca-http.error.log` (and the `.1`, `.2.gz`, `.3.gz`, etc historical versions).

### Gunicorn/Django

Gunicorn is responsible for running the application itself. It's installed by our recipe and is controlled as a Systemd service `/etc/systemd/system/gunicorn.service` (generated by our `deploy/cookbooks/coursys/templates/gunicorn.service.erb`). Thus it can be restarted with `sudo service gunicorn restart` (but that's likely never necessary to do manually).

Some information about the way the process started is in the systemd logs: `sudo journalctl -u gunicorn`

Gunicorn's main log file is `/opt/logs/gunicorn-error.log`.

### Celery

Celery is responsible for running tasks. It's installed by our recipe and is controlled as a Systemd service `/etc/systemd/system/celery.service` (generated by our `deploy/cookbooks/coursys/templates/celery.service.erb`). Thus it can be restarted with `sudo service celery restart` (but that's likely never necessary to do manually).

Some information about the way the process started is in the systemd logs: `sudo journalctl -u celery`

Celery's main log file are `/opt/logs/celery-*`. A separate log file is kept for each queue/worker.


## Server Updates

```shell
sudo apt update
sudo apt upgrade
```

## Deploying code

different user: handling it
```shell
sudo -E -u coursys HOME=/home/coursys ./manage.py shell
```

### The Usual Case

Almost all the time, the procedure is:

1. Accept a pull request into the master branch, or push into master.
2. Log on to the production server.
3. Get the code: `make pull`.
4. Get that code running: `make new-code`. This reloads/restarts the gunicorn and celery processes.
4. Make sure our deployment checks pass:  System Administration -> View Admin Panel -> Deployment Checks
5. Maybe also make sure emails are going through: the admin panel Email Check tab.



### With a Database Migration

If it's necessary to do a database migration, it's probably worth putting the server into "503 unavailable" mode to make sure nothing happens in an inconsistent state.

```shell
make 503
make pull
make migrate-safe  # takes database snapshots before and after migration
make manage ARGS=check_things
make new-code
make rm503
```



### With a Library/Module Change

If you have a library/dependency change, the `make rebuild` 

```shell
make 503
make pull
make rebuild  # includes a "make new-code"
make manage ARGS=check_things
make rm503
```


## In Case of Problems

If the application isn't running properly, the gunicorn logs can be useful, but it's often much easier and faster to just start a Django shell. If the application code is throwing an exception, it will likely be visible here.
```shell
make shell
```

If the problem is with data or a little more subtle, in the Django shell, you can inspect data objects or call methods on them manually (while being cautious of side effects) to see what is happening.
```python
from coredata.models import *
p = Person.objects.get(userid="problem")
p.__dict__
p.search_label_value()
```

A database dump is done every few hours in production into `/filestore/prod/db_backup/`. In a worst-case scenario, these can be examined for changes in the database and/or information on what has been happening.

Running manage.py will often trigger whatever error is happening, in a more helpful environment
run things manually as a temporary last resort

As a last resort, it's possible to run components of the system manually. This is almost certainly a bad idea, but may provide a way to diagnose problems that aren't otherwise visible.
```shell
sudo -E -u coursys HOME=/home/coursys python3 manage.py runserver
sudo -E -u coursys HOME=/home/coursys python3 /usr/local/bin/celery -A courses worker -l INFO
```




