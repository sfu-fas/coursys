# Demo Server Setup

## Basic Server Setup

Create a VM, with likely specs 2 cores, 8GB memory, 30GB disk.

This replicates enough of the RHEL server setup recipe:
```shell
COURSYS_USERNAME=coursys
COURSYS_UID=888
COURSYS_HOME=/home/${COURSYS_USERNAME}
SOURCE_LOCATION=/coursys
BRANCH=master
DATA_PREFIX=/data/
DOCKER_COMPOSE_FILE='compose-demo.yml'

# set up user and code
sudo useradd --uid ${COURSYS_UID} --home-dir ${COURSYS_HOME} ${COURSYS_USERNAME}
sudo mkdir ${SOURCE_LOCATION}
sudo git clone https://github.com/sfu-fas/coursys.git -b ${BRANCH} ${SOURCE_LOCATION}
sudo chown -R ${COURSYS_USERNAME} ${SOURCE_LOCATION}

# basic config choices
sudo ln -sf ${SOURCE_LOCATION}/${DOCKER_COMPOSE_FILE} ${SOURCE_LOCATION}/compose.yml
install -o root -m 0700 -d ${SOURCE_LOCATION}/secrets
[ -f ${SOURCE_LOCATION}/secrets/app-config.toml ] || install -o root -m 0644 ${SOURCE_LOCATION}/docker/app-config-template.toml ${SOURCE_LOCATION}/secrets/app-config.toml

# data directories & permissions
sudo install -o root -d ${DATA_PREFIX}
sudo install -o ${COURSYS_USERNAME} -d ${DATA_PREFIX}submitted_files ${DATA_PREFIX}db_backups ${DATA_PREFIX}csrpt_auth ${DATA_PREFIX}dynamic_config
install -o 1000 -d ${DATA_PREFIX}elasticsearch7

sudo apt-get install -y make docker-compose-v2 docker-buildx
sudo gpasswd -a `whoami` docker
```


## Starting Docker Containers

Log out and back in so the group membership takes effect and...
```shell
cd /coursys
make get-docker-rollout
docker compose pull
docker compose build
docker compose up -d mysql elasticsearch rabbitmq memcached
docker compose run manage migrate
docker compose run manage collectstatic --no-input
docker compose up --remove-orphans -d
```


## Demo Data

For the demo system, we use a mix of real-but-public data, and enough fake data to work with.

On the *production* server, capture the basic public info we want to have:
```shell
./manage.py dump_demo_data > /tmp/demodata.json
```

Copy `demodata.json` to the demo server and **on the demo server**:
```shell
cd /coursys
sudo cp ~/demodata.json ./demodata.json
sudo chmod 0644 ./demodata.json
docker compose build
docker compose run manage load_demo_data ./demodata.json
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
