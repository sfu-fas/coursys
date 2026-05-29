* kinit auth piped in somehow
* submission dir
* DB backup dir
* maintenance mode/503 handling
* logrotate


## Compose Notes

For mostly-production-like like deployment:
```sh
docker compose -f docker-compose-demo.yml pull
docker compose -f docker-compose-demo.yml build --pull
docker compose -f docker-compose-demo.yml up -d mysql elasticsearch
docker compose -f docker-compose-demo.yml run app ./manage.py migrate
docker compose -f docker-compose-demo.yml run app ./manage.py collectstatic --no-input
docker compose -f docker-compose-demo.yml run app ./manage.py loaddata fixtures/*
docker compose -f docker-compose-demo.yml run app ./manage.py update_index
docker compose -f docker-compose-demo.yml up --remove-orphans -d
```

To update:
```sh
docker compose -f docker-compose-demo.yml build
docker compose -f docker-compose-demo.yml up -d app celery
# or with https://github.com/wowu/docker-rollout
docker compose -f docker-compose-demo.yml build
docker rollout -f docker-compose-demo.yml --wait-after-healthy 5 app
docker rollout -f docker-compose-demo.yml --wait-after-healthy 5 celery
```

To destroy:
```sh
docker compose -f docker-compose-demo.yml stop
docker compose -f docker-compose-demo.yml rm
docker system prune
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
* `/etc/krb5.conf` has something to do with all of this, probably.
* Possibly helpful:
    * https://stackoverflow.com/questions/56382414/unable-to-connect-to-microsoft-sql-server-inside-docker-container-using-freetds
