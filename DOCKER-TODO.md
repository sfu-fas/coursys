# TODO

* kinit auth creation/refreshing logic (kinit*.sh actually hooked up somewhere)
* docs for prod setup
* update SYSADMIN.md
* who is going to own /coursys/*? Makefile implies it's `coursys`, instrutions imply root.
* do we need/want to restart celery and/or celerybeat in cron?
* fix the compress test if directory hasn't been created yet
* check_things test for CSRPT will always fail since /csrpt_auth isn't there
* volume for logrotate status?

# Notes

## Build Network Access

We have an HTTP proxy for outside works access (git clones, etc). See: https://docs.docker.com/engine/cli/proxy/#configure-the-docker-client

## Compose Notes

For mostly-production-like deployment:
```sh
#DOCKERCOMPOSE="docker compose --env-file docker/demo.env -f compose-demo.yml"
#DOCKERROLLOUT="docker rollout --env-file docker/demo.env -f compose-demo.yml"
DOCKERCOMPOSE="docker compose -f /coursys/compose.yml"
DOCKERROLLOUT="docker rollout -f /coursys/compose.yml"
${DOCKERCOMPOSE} pull
${DOCKERCOMPOSE} build
${DOCKERCOMPOSE} up -d mysql elasticsearch rabbitmq memcached
${DOCKERCOMPOSE} run manage migrate
${DOCKERCOMPOSE} run manage collectstatic --no-input
${DOCKERCOMPOSE} run manage loaddata fixtures/*
${DOCKERCOMPOSE} run manage update_index
${DOCKERCOMPOSE} up --remove-orphans -d
```

To update:
```sh
${DOCKERCOMPOSE} build --pull
${DOCKERCOMPOSE} run app ./manage.py collectstatic --no-input
${DOCKERCOMPOSE} up -d
# or with https://github.com/wowu/docker-rollout
${DOCKERCOMPOSE} build --pull
${DOCKERCOMPOSE} run app ./manage.py collectstatic --no-input
${DOCKERROLLOUT} --wait-after-healthy 5 app
${DOCKERCOMPOSE} up --remove-orphans -d "celery*"
docker system prune
```

To destroy:
```sh
${DOCKERCOMPOSE} stop
${DOCKERCOMPOSE} rm
docker system prune --volumes
#docker volume prune -a
```


## Swarm Notes

I'm probably going to leave well enough alone and just use compose, but for the record...

```sh
docker swarm init --advertise-addr 10.0.0.2
docker stack deploy -c docker-compose-registry.yml registry
docker compose config > dc.yml
docker compose -f dc.yml build
docker compose -f dc.yml push
docker stack deploy -c dc.yml coursys
```

```sh
docker exec $(docker ps -q -f name=coursys_app | head -n1) ./manage.py migrate
docker exec $(docker ps -q -f name=coursys_app | head -n1) ./manage.py collectstatic --no-input
docker exec $(docker ps -q -f name=coursys_app | head -n1) ./manage.py loaddata fixtures/*
docker exec $(docker ps -q -f name=coursys_app | head -n1) ./manage.py update_index
```

```sh
docker service ls
```


## CSRPT Authentication

Things I have learned...

* In `coredata/queries.py`, we use `pyodbc.connect` to connect to CSRPT.
* `pyodbc` uses the FreeTDS driver, which knows how to connect to SQL Server in general.
    * Connection string is essentially: `"DRIVER={FreeTDS};SERVER=[redacted].dc.sfu.ca';PORT=1433;DATABASE=CSRPT;Trusted_Connection=Yes"`
* In the pyodbc connection string, "`Trusted_Connection=Yes`" indicates that it should use current "user account", which I believe is where Kerberos comes into the picture.
* Our `kinit.sh` that does the Kerberos auth...
    * Runs several commands in `ktutil`. That creates `~/kerberos/adsfu.keytab`.
    * Runs `kinit ${USERNAME}@AD.SFU.CA -k -t ~/kerberos/adsfu.keytab` to get a ticket that (seems to be what) is actually used to authenticate.
    * Running `kinit` creates a file `/tmp/krb5cc_${UID}`.
* That `kinit` command is run in `kinit.sh` and in a cron job to refresh the ticket, updating the file in `/tmp` but **not** the `adsfu.keytab`.
* I infer that FreeTDS must read that file from `/tmp` to authenticate.
* Possibly we can copy/mount the `~/kerberos` contents into the container, and run the `kinit` as part of the container startup?
* Possibly helpful:
    * https://stackoverflow.com/questions/56382414/unable-to-connect-to-microsoft-sql-server-inside-docker-container-using-freetds

* Something that works:
    * container with `krb5-user` installed.
    * manually with bash in the container: `kinit username@AD.SFU.CA`, thus creating `/tmp/krb5cc_${UID}`;
    * run `tsql`.
    * Also: manually doing the steps from `kinit.sh` works in the container.
* Also works:
    * Creating `/tmp/krb5cc_${UID}` for an arbitrary user *outside* docker entirely,
    * ... then copying that file into the image in as `/tmp/krb5cc_12345`.
* Also works:
    * Copying/mounting in the `adsfu.keytab` in; in the container, doing: `kinit ${USERNAME}$@AD.SFU.CA -k -t /tmp/adsfu.keytab`

Testing in the shell:
```
docker compose -f docker-compose-csrpt-test.yml build
docker compose -f docker-compose-csrpt-test.yml run csrpt-test bash
tsql -S ss-csrpt-db1.dc.sfu.ca -D CSRPT
SELECT * FROM PS_TERM_TBL WHERE ACAD_YEAR='2012'
go
```

Testing connection in Python:
```
docker compose -f docker-compose-csrpt-test.yml build
docker compose -f docker-compose-csrpt-test.yml run csrpt-test python3
```
```py
import pyodbc
(SIMS_DB_SERVER, SIMS_DB_NAME) = ('ss-csrpt-db1.dc.sfu.ca', 'CSRPT')
dbconn = pyodbc.connect("DRIVER={FreeTDS};SERVER=%s;PORT=1433;DATABASE=%s;Trusted_Connection=Yes" % (SIMS_DB_SERVER, SIMS_DB_NAME))
c = dbconn.execute("SELECT * FROM PS_TERM_TBL WHERE ACAD_YEAR='2012'", ())
list(c)
```

Possible manual creation of certificate:
```shell
docker compose run celery-sims /coursys/kinit.sh
```
And regular refresh. Could this be done in a periodic task?
```shell
docker compose run celery-sims /coursys/kinit-refresh.sh
```


## Auth Details

Authenticating to CSRPT as we do in production is a two-step process. We are using Kerberos to authenticate to the MSSQL Server.

Step 0: `/etc/krb5.conf` is put in place by our Docker recipe, indicating how Kerberos authentication is to be done.

To start, `kinit.sh` needs to be run by a human: it needs a username and password. It uses them to contact the Active Directory server and retrieves a Kerberos keytab. That is stored (inside the container) as `/csrpt_auth/adsfu.keytab`. The `kinit.sh` script also executes step 2...

Next, `kinit-refresh.sh` uses that keytab to request a ticket. The ticket has a modest lifespan, so this must be periodicly refreshed, but it can be done hand-free. This creates a `/tmp/krb4cc_${UID}` file, which we symlink from `/csrpt_auth`.

The `/csrpt_auth` directory is mounted on all containers that need CSRPT auth. When we use pyodbc to actually connect to CSRPT, it reads `/tmp/krb4cc_${UID}`.



## Data Center Notes

```bash
http_proxy="http://bby-vcontrol-proxy.its.sfu.ca:8080"
https_proxy="http://bby-vcontrol-proxy.its.sfu.ca:8080"
```

Maybe `/etc/docker/daemon.json`:
```json
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "syslog",
  "storage-driver": "overlay2",
  "iptables": true,

  "bip": "10.131.0.1/16",
  "fixed-cidr": "10.131.0.0/17",
  "default-address-pools":[
      {"base":"10.132.0.0/16","size":24}
  ],

  "proxies": {
   "default": {
     "httpProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
     "httpsProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
     "noProxy": "cas.sfu.ca,.sfu.ca,localhost"
   }
 }
}
```


