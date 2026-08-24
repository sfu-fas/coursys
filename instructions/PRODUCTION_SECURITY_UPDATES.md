# Security Updates in Production

We should do regular updates of our dependencies in production to get security updates on our docker base images, etc.

## Local Tests

A little local testing is likely wise, to make sure things work as expected with the container builds.

Build updated container images:
```shell
# If necessary: ln -s compose-proddev.yml compose.yml
docker compose pull
docker compose build --pull --no-cache
```

Run our Django tests:
```shell
docker compose run manage test
```

And bring the system up and run the deployment tests:
```shell
docker compose up -d
docker compose ps  # wait until things are healthy
docker compose run manage check_things
```
In this context, we expect system checks related to external APIs to fail: reporting database/CSRPT, photo API, emplid API, moss integration.


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
