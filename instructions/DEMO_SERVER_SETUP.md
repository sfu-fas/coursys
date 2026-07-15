# Demo Server Setup

## Basic Server Setup

Create a VM, with likely specs 2 cores, 8GB memory, 30GB disk.

This replicates enough of the RHEL server setup recipe:
```shell
COURSYS_USERNAME=coursys
COURSYS_UID=888
COURSYS_HOME=/home/${COURSYS_USERNAME}
SOURCE_LOCATION=/coursys
BRANCH=docker-deploy
DATA_PREFIX=/data/
DOCKER_COMPOSE_FILE='compose-demo.yml'

# set up user and code
sudo useradd --uid ${COURSYS_UID} --home-dir ${COURSYS_HOME} ${COURSYS_USERNAME}
sudo mkdir ${SOURCE_LOCATION}
sudo git clone https://github.com/sfu-fas/coursys.git -b ${BRANCH} ${SOURCE_LOCATION}
sudo chown -R ${COURSYS_USERNAME} ${SOURCE_LOCATION}

# basic config choices
sudo ln -sf ${SOURCE_LOCATION}/${DOCKER_COMPOSE_FILE} ${SOURCE_LOCATION}/compose.yml
[ -f ${SOURCE_LOCATION}/secrets/app-config.toml ] || sudo install -o root -m 0644 ${SOURCE_LOCATION}/secrets/app-config-template.toml ${SOURCE_LOCATION}/secrets/app-config.toml
[ -f ${SOURCE_LOCATION}/secrets/rabbitmq-default-password ] || echo "rmqpass" | sudo tee ${SOURCE_LOCATION}/secrets/rabbitmq-default-password
[ -f ${SOURCE_LOCATION}/secrets/elastic-initial-password ] || echo "espass" | sudo tee ${SOURCE_LOCATION}/secrets/elastic-initial-password

# data directories & permissions
sudo install -o root -d ${DATA_PREFIX}
sudo install -o ${COURSYS_USERNAME} -d ${DATA_PREFIX}submitted_files ${DATA_PREFIX}db_backups ${DATA_PREFIX}csrpt_auth ${DATA_PREFIX}dynamic_config ${DATA_PREFIX}celery_logs
sudo install -o 1000 -d ${DATA_PREFIX}elasticsearch7

sudo apt-get install -y make docker-compose-v2 docker-buildx
sudo gpasswd -a `whoami` docker
```
Log out and back in so the group membership takes effect.


## Starting Docker Containers

```shell
cd /coursys
make get-docker-rollout
docker compose pull
docker compose build --pull
docker compose up -d mysql elasticsearch rabbitmq memcached
docker compose run manage migrate
docker compose run manage collectstatic --no-input
docker compose up --remove-orphans -d
```


## Demo Data

Demo data can be fetched from the production server, giving a secret key that is the first 6
characters of the server secret (technically, `urllib.parse.quote(settings.SECRET_KEY[:6])`).
```shell
curl https://coursys.sfu.ca/sysadmin/demo_data?key=abc123 > /tmp/demodata.json
```

Then, **on the demo server**:
```shell
sudo cp /tmp/demodata.json /data/dynamic_config/
sudo chmod 0644 /data/dynamic_config/demodata.json
docker compose run manage load_demo_data /dynamic_config/demodata.json
docker compose run manage rebuild_index --noinput
```


## Purging Data

If we'd like to refresh with a new `demodata.json`, the database must be purged:
```shell
cd /coursys
docker compose stop
docker compose rm mysql
docker volume rm coursys_mysql
docker compose up -d
docker compose run manage migrate
```
And repeat the "Demo Data" loading above.
