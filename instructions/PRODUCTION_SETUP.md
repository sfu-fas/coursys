# Production Server Setup

The scripts in `rhel/` should be able to set up the basics on the server, with this `rhel/config.sh`:
```bash
USERNAME=ggbaker
USER_HOME=/home/${USERNAME}
COURSYS_USERNAME=coursys
COURSYS_UID=888
COURSYS_HOME=/home/${COURSYS_USERNAME}
SOURCE_LOCATION=/coursys
BRANCH=docker-deploy
DATA_PREFIX=/data/
DOCKER_COMPOSE_FILE='compose-production.yml'
```


```shell
touch ./this_is_production.txt
cp docker/app-config-template.toml secrets/app-config.toml
make get-docker-rollout
```

Edit `secrets/app-config.toml` to reflect the production setup.



## Pending

* we probably need our IP address whitelisted for some of the external services: CSRPT, CAS, phtos API, AMAINT
* load balancer switchover
* database main server migration
* submitted files migration (and file ownership?)