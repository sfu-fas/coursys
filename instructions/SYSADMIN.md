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

## Web Server

The frontend web server is Nginx, which serves static files and proxies dynamic requests to Gunicorn. Its logs are in `/opt/nginx-logs/`. 

We are using Let's Encrypt SSL/TLS certificates. A cron job runs `certbot renew` weekly, and should automatically update certificates as needed.

## System Checks

The system knows how to check its deployment environment quite thoroughly. These checks can be triggered with one of these commands (depending on currently-active user):
```shell
make manage ARGS=check_things
python3 manage.py check_things
```
Or visit https://coursys.sfu.ca/sysadmin/panel (as an account with system admin role) and check the "Deployment Checks" tab.

## CSRPT Tunnel

An SSH tunnel to the reporting database must be created manually on system restart (or if it drops).
The most effective way to do this seems to be to start a screen session (`screen`), start this command, and exit the screen session (ctrl-a d).
```shell
ssh -L 127.0.0.1:50000:hutch.ais.sfu.ca:50000 -o ServerAliveInterval=60 -N USERNAME@pf.sfu.ca
```
A periodic task will email `settings.ADMINS` if the tunnel is down.


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