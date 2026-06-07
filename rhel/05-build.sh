#!/bin/sh

set -e
source ./config.sh

install -o root -d ${DATA_PREFIX}rabbitmq3
install -o coursys -d ${DATA_PREFIX}submitted_files ${DATA_PREFIX}db_backups ${DATA_PREFIX}csrpt_auth ${DATA_PREFIX}dynamic_config
install -o 101 -g 101 -d ${DATA_PREFIX}nginx_logs ${DATA_PREFIX}elasticsearch5

cd ${SOURCE_LOCATION}
ln -sf ${DOCKER_COMPOSE_FILE} docker-compose.yml
docker compose pull
docker compose build --pull