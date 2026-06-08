COURSYS_USER=coursys
COURSYS_USER_HOME=/home/${COURSYS_USER}

SUCOURSYS=sudo -E -u ${COURSYS_USER} HOME=${COURSYS_USER_HOME}
DOCKERCOMPOSE=docker compose
DOCKERROLLOUT=docker rollout

start-all:
	${DOCKERCOMPOSE} up -d

pull:
	${SUCOURSYS} git pull

pull-rebuild:
	${SUCOURSYS} git pull
	${DOCKERCOMPOSE} pull
	${DOCKERCOMPOSE} build --pull

rebuild:
	${DOCKERCOMPOSE} build

redeploy:
	${DOCKERCOMPOSE} run manage collectstatic --no-input
	${DOCKERROLLOUT} --wait-after-healthy 5 app  # zero-downtime rollout of app service
	${DOCKERCOMPOSE} up --remove-orphans -d      # restart celery and anything else changed

new-code: rebuild redeploy

migrate-safe:
	${DOCKERCOMPOSE} run manage backup_db_task
	${DOCKERCOMPOSE} run manage migrate
	${DOCKERCOMPOSE} run manage backup_db_task

purge-cache:  # if we have changed something in a way that breaks cached data: shouldn't happen, but just in case
	${DOCKERCOMPOSE} run manage purge_cache

purge-static:  # shouldn't be necessary in general, but just in case we want to tidy the static volume
	sudo touch /data/dynamic_config/503
	${DOCKERCOMPOSE} run app rm -r /static/static
	${DOCKERCOMPOSE} run manage collectstatic --no-input
	make purge-cache  # django-compressor caches what has already been built
	sudo rm /data/dynamic_config/503

503:
	sudo touch /data/dynamic_config/503
	${DOCKERCOMPOSE} down `${DOCKERCOMPOSE} config --services | grep -e '^celery'`

rm503:
	sudo rm /data/dynamic_config/503
	${DOCKERCOMPOSE} up -d


# management helpers

shell:
	${DOCKERCOMPOSE} run manage shell
dbshell:
	${DOCKERCOMPOSE} run manage dbshell
get-docker-rollout:
	mkdir -p ~/.docker/cli-plugins
	wget https://github.com/wowu/docker-rollout/releases/download/v0.13/docker-rollout -O ~/.docker/cli-plugins/docker-rollout
	chmod +x ~/.docker/cli-plugins/docker-rollout