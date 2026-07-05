# TODO

* do we need/want to restart celery and/or celerybeat in cron?
* need some protocol for regular dnf updates and docker pulls
* some monitoring of docker containers/usage/etc?
* finalize sudo config in prod
* what if we rebooted automatically at 4:30 on Sundays or something?


Probable update procedure...


## Local Tests

Run our Django tests:
```shell
# If necessary: ln -s compose-proddev.yml compose.yml
docker compose pull
docker compose build --pull --no-cache
docker compose run manage test
```

And bring the system up and run the deployment tests:
```shell
docker compose up -d
docker compose run manage check
docker compose run manage check_things
```

## On The Server

```shell
sudo dnf -y update
docker system prune
cd /coursys
make new-code-pull
docker compose run manage check_things
```

Make sure all containers become healthy in `docker ps`.

In the event of any network problems, probably `sudo service docker restart` to restore Docker's iptables setup.
