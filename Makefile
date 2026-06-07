COURSYS_USER=coursys
COURSYS_USER_HOME=/home/${COURSYS_USER}

SUCOURSYS=sudo -E -u ${COURSYS_USER} HOME=${COURSYS_USER_HOME}
#DOCKERCOMPOSE=${SUCOURSYS} docker compose
DOCKERCOMPOSE=docker compose -f /coursys/docker-compose.yml
DOCKERROLLOUT=docker rollout -f /coursys/docker-compose.yml

start-all:
	${DOCKERCOMPOSE} up -d

pull-rebuild:
	${SUCOURSYS} git pull
	${DOCKERCOMPOSE} pull
	${DOCKERCOMPOSE} build --pull

rebuild:
	${DOCKERCOMPOSE} build

redeploy:
	${DOCKERCOMPOSE} run manage collectstatic --no-input
	${DOCKERROLLOUT} --wait-after-healthy 5 app  # zero-downtime rolling restart of app service
	${DOCKERCOMPOSE} up --remove-orphans -d      # restart celery and anything else changed
	docker system prune -f

new-code: rebuild redeploy

migrate-safe:
	${DOCKERCOMPOSE} run manage backup_db_task
	${DOCKERCOMPOSE} run manage migrate
	${DOCKERCOMPOSE} run manage backup_db_task

purge-cache:
	${DOCKERCOMPOSE} run manage purge_cache

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
