COURSYS_USER=coursys

GIT=sudo -u ${COURSYS_USER} git
DOCKERCOMPOSE=docker compose
DOCKERROLLOUT=docker rollout

start-all:
	${DOCKERCOMPOSE} up -d --remove-orphans

pull:
	${GIT} pull

pull-build:
	${GIT} pull
	${DOCKERCOMPOSE} pull
	${DOCKERCOMPOSE} build --pull --no-cache

build:
	${DOCKERCOMPOSE} build

deploy:
	${DOCKERCOMPOSE} run manage collectstatic --no-input
	${DOCKERROLLOUT} --timeout 120 --wait-after-healthy 5 app  # zero-downtime rollout of app service
	${DOCKERCOMPOSE} up -d --remove-orphans                    # restart celery and anything else changed

deploy-no-rollout:  # skips the "docker rollout" in favour of a faster "up -d" with a few seconds of downtime
	${DOCKERCOMPOSE} run manage collectstatic --no-input
	${DOCKERCOMPOSE} up -d --remove-orphans

new-code: build deploy

new-code-pull: pull-build deploy

new-code-no-rollout: build deploy-no-rollout

migrate-safe:
	${DOCKERCOMPOSE} run manage backup_db_task
	${DOCKERCOMPOSE} run manage migrate
	${DOCKERCOMPOSE} run manage backup_db_task

purge-cache:  # if we have changed something in a way that breaks cached data: shouldn't happen, but just in case
	${DOCKERCOMPOSE} run manage purge_cache

purge-static:  # shouldn't be necessary in general, but just in case we want to tidy the static volume
	${DOCKERCOMPOSE} run admin touch /dynamic_config/503
	${DOCKERCOMPOSE} run admin rm -r /static/static
	${DOCKERCOMPOSE} run manage collectstatic --no-input
	make purge-cache  # django-compressor caches what has already been built: force it to re-check
	${DOCKERCOMPOSE} run admin rm /dynamic_config/503

drain-tasks:  # make absolutely sure there are no pending tasks (i.e. that rabbitmq can be purged during an upgrade/migration)
	${DOCKERCOMPOSE} run admin touch /dynamic_config/503
	${DOCKERCOMPOSE} stop beat
	echo "Watch celery_logs until nothing else is being processed. Then you can safely purge/restore rabbitmq and 'make rm503'"

503:  # ensure that the system is down in such a way that no database/file changes are happening
	${DOCKERCOMPOSE} run admin touch /dynamic_config/503
	${DOCKERCOMPOSE} stop `${DOCKERCOMPOSE} config --services | grep -e '^celery'`

rm503:
	${DOCKERCOMPOSE} run admin rm /dynamic_config/503
	${DOCKERCOMPOSE} up -d


# admin helpers

shell:
	${DOCKERCOMPOSE} run manage shell
dbshell:
	${DOCKERCOMPOSE} run manage dbshell
admin:
	${DOCKERCOMPOSE} run admin bash

get-docker-rollout:  # should be installed globally in prod, but for dev environments, a handy fetcher...
	mkdir -p ~/.docker/cli-plugins
	wget https://github.com/wowu/docker-rollout/releases/download/v0.13/docker-rollout -O ~/.docker/cli-plugins/docker-rollout
	chmod +x ~/.docker/cli-plugins/docker-rollout