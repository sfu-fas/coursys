#!/bin/sh

source vars.sh

install -o root -d ${DATA_PREFIX}rabbitmq3
install -o coursys -d ${DATA_PREFIX}submitted_files ${DATA_PREFIX}db_backups ${DATA_PREFIX}dynamic-config
install -o 101 -g 101 -d ${DATA_PREFIX}nginx_logs # ${DATA_PREFIX}elasticsearch5

DOCKERCOMPOSE="docker compose --env-file docker/demo.env -f docker-compose-demo.yml"
DOCKERROLLOUT="docker rollout --env-file docker/demo.env -f docker-compose-demo.yml"
${DOCKERCOMPOSE} pull
${DOCKERCOMPOSE} build