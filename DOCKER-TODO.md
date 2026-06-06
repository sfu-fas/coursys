# TODO

* kinit auth piped in somehow
* log files. Proposal:
    * nginx https://alexanderzeitler.com/articles/rotating-nginx-logs-with-docker-compose/
    * everything else to syslog
* maintenance mode/503 handling
* logrotate
* MOSS

# Notes

## Build Network Access

We have an HTTP proxy for outside works access (git clones, etc). See: https://docs.docker.com/engine/cli/proxy/#configure-the-docker-client

## Compose Notes

For mostly-production-like deployment:
```sh
DOCKERCOMPOSE="docker compose --env-file docker/demo.env -f docker-compose-demo.yml"
DOCKERROLLOUT="docker rollout --env-file docker/demo.env -f docker-compose-demo.yml"
DOCKERCOMPOSE="docker compose -f docker-compose-demo.yml"
DOCKERROLLOUT="docker rollout -f docker-compose-demo.yml"
${DOCKERCOMPOSE} pull
${DOCKERCOMPOSE} build
${DOCKERCOMPOSE} up -d mysql elasticsearch rabbitmq
${DOCKERCOMPOSE} run app ./manage.py migrate
${DOCKERCOMPOSE} run app ./manage.py collectstatic --no-input
${DOCKERCOMPOSE} run app ./manage.py loaddata fixtures/*
${DOCKERCOMPOSE} run app ./manage.py update_index
${DOCKERCOMPOSE} up --remove-orphans -d
```

To update:
```sh
${DOCKERCOMPOSE} build --pull
${DOCKERCOMPOSE} up -d
# or with https://github.com/wowu/docker-rollout
${DOCKERCOMPOSE} build --pull
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
docker compose -f docker-compose-demo.yml build
docker compose -f docker-compose-demo.yml push
docker stack deploy -c docker-compose-demo.yml coursys
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
  "bip": "10.131.0.1/16",
  "fixed-cidr": "10.131.0.0/17",
  "iptables": true,
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


