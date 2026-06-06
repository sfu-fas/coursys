#!/bin/sh

set -e
source ./config.sh

install -o root -d ${DATA_PREFIX}rabbitmq3
install -o coursys -d ${DATA_PREFIX}submitted_files ${DATA_PREFIX}db_backups ${DATA_PREFIX}dynamic_config
install -o 101 -g 101 -d ${DATA_PREFIX}nginx_logs ${DATA_PREFIX}elasticsearch5

cd ${SOURCE_LOCATION}
docker compose ${DOCKER_ARGS} pull
docker compose ${DOCKER_ARGS} build