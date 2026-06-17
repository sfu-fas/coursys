# Production Server Setup

These instructions cover deploying and configuring a new production server.

There are some additional notes (of details that we don't make public) in the CourSys Team:
Teams -> CourSys -> General -> Shared -> production access.docx.

## A New Web Server

### Server Creation

1. Get an appropriate VM: probably 4 CPU cores, 16GB memory, 100GB root volume.
2. Mount the NFS share that holds our file data on `/filestore`.
3. Ensure the production database server is accessible (i.e. connection on port 3306 is possible).

TODO Other external APIs we access: CSRPT, CAS, photos API, AMAINT


### Bootstrapping

The commands in `rhel/01-bootstrap.sh` are intended to be run manually to get the code in place.

After that, the scripts in `rhel/` should be able to set up the basics on the server. Have a look
at `rhel/config.sh` first, Contents likely something like:
```bash
USERNAME=ggbaker-pam
USER_HOME=/home/${USERNAME}
COURSYS_USERNAME=coursys
COURSYS_UID=6501
COURSYS_HOME=/home/${COURSYS_USERNAME}
SOURCE_LOCATION=/coursys
DATA_PREFIX=/data/
DOCKER_COMPOSE_FILE='compose-production.yml'
```

Consider setting `DO_IMPORTING_HERE = False` in `courses/docker-localsettings-production.py`
temporarily while setting up: it's intended to ensure there's no split-brain on any critical data
updates during a transition like this.

Review and run scripts 02-05. Have a look around and make sure things are as expected. You may have
to log out and back in after 03 to get the docker group membership active.

Get the system firmly into production mode:
```shell
touch ./this_is_production.txt  # now the system will refuse to start in anything but production mode.
cp secrets/app-config-template.toml secrets/app-config.toml
echo "rmqpass" > ./secrets/rabbitmq-default-password
echo "espass" > ./secrets/elastic-initial-password
```
Edit the secrets to reflect the real production setup. In particular, the SECRET_KEY (in
app-config.toml as "django_secret") must match the old server. Otherwise all users will be logged
out during the migration.

Likely copy the contents of the `moss` directory from the old server. The file `moss/moss.pl`
should exist.


### Getting Started & Checks

It's likely safe to start the background services:
```shell
docker compose up -d rabbitmq elasticsearch memcached  # if following this in proddev mode, probably also mysql and smtp4dev
```

The system is fairly good at inspecting itself. Consider:
```shell
docker compose run manage check         # the standard Django system checks (The system would refuse to start on errors here.)
docker compose run manage check_things  # our deeper inspection of the state of the deployment
```
The check_things should find that Celery isn't running at this point, which is expected.

To test the photos API, we would need those celery workers up (but fetching ID photos is the *only* thing they do):
```shell
docker compose up -d celery-photo
docker compose run manage check_things
docker compose down celery-photo
```

To test email sending, that celery worker needs to be up:
```shell
docker compose up -d celery-email
docker compose run manage check_things --email=whoever@sfu.ca
docker compose down celery-email
```

### External Services

* CAS: ???
* Photos API: seems to just work (given the password that's reguarly rotated and stored in the database).
* CSRPT: seems to work once the auth stuff is bootstrapped.
* AMAINT/EMPLID API: needs whitelisting.
* email sending: historically just works.


### Actually Switching Over

If database access is okay, and Elastic search is up, the indexing can be started ahead of time:
```shell
docker compose up -d celery-batch
docker compose run manage update_index_task --full-rebuild
```

Actually starting the full system:
```shell
docker compose up -d
docker compose run manage check_things
```

If time is on your side, and both the database server and NFS share are common to the old and new
deployments, consider having the SFU load balancer point a temporary domain name at this new
server. Then you can exercise it at your leisure.

Finally, have the SFU load balancer point the coursys.sfu.ca name at the new server.



## Pending

* we probably need our IP address whitelisted for some of the external services: CSRPT, CAS, photos API, AMAINT
* load balancer switchover
* database main server migration
* submitted files migration (and file ownership?)



## Database Server Migration

When we have updated the MariaDB server in the past, the process was something like this:

0. A few days before, add a note warning of downtime in `SERVER_MESSAGE_INDEX` in `courses/docker-localsettings-production.py`.
1. Stop the world: `make 503`. Likely also bring down Docker services to ensure no database updates are happening.
2. Do the actual database migration: `mysqldump` on the old server, and restore that dump on the new.
3. Do a few queries (below) against the old database server, so we can sanity check the new one.
4. Consider doing our own `manage.py backup_db` simultaneously, just to have that format.
5. While that's happening, update the hostname of the database server, likely in `secrets/app-config.toml`.
6. Remove the downtime warning.
7. Even before the database is fully restored, admins can run a Django shell or dbshell to make sure connections work and things are being populated as expected. Also check the server version is as-expected.
8. Once the database is restored, repeat the sanity-check queries (below) to make sure everything looks the same.
9. `make new-code` and `make rm503`.
10. Have a look at the deployment checks in the sysadmin panel.

The sanity queries we repeated with both DB servers last time:
```py
from coredata.models import *
from log.models import *
RequestLog.objects.all().order_by('-time').first()
CeleryTaskLog.objects.all().order_by('-time').first()
Member.objects.count()
```

## Files/NFS Migration

This hasn't been done in recent memory, but the issue here is potentially moving to a new server
for the directory mounted at `/submitted_files` in the Docker containers. These instructions are
**untested**.

It should be possible to do an `rsync` of that directory from an old to new server well ahead of
time. Since files are now only created in `YEAR/MONTH` directories, any new additions should be
predictable.

Once ready, do a "stop the world" as described in the database migration, and `rsync` the monthly
directory where any new files would have appeared. Record the output of `find` on each. Compare
the `find` output to make sure all expected files are there.

Switch the Docker `/submitted_files` mount, or mount the file volume in place of the old. Restart.