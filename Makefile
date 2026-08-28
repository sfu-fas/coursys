COURSYS_USER=coursys

GIT=sudo -u ${COURSYS_USER} git
DOCKERCOMPOSE=docker compose
# containers where our code runs, which are usually all that need to be rebuilt:
CODE_CONTAINERS=beat admin manage `${DOCKERCOMPOSE} config --services | grep -e '^app' -e '^celery'`


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

build-code-containers:  # we almost never need containers without our code rebuilt, so don't by default.
	${DOCKERCOMPOSE} build ${CODE_CONTAINERS}

rollout:  # a zero-downtime switchover from old to new container images, rolling between app-a and app-b
	# What's happening here: /dynamic_config/nginx-backends.conf is juggled to select app-* backend(s), and SIGHUP to nginx tells it to seamlessly reload its config.
	# Then while each app-* container is being ignored by nginx, it's restarted.
	# drain requests to app-a
	${DOCKERCOMPOSE} run -q --remove-orphans admin cp docker/nginx/backend-configs/drain-a.conf /dynamic_config/nginx-backends.conf
	${DOCKERCOMPOSE} kill --remove-orphans -s SIGHUP nginx && sleep 2
	# restart app-a
	${DOCKERCOMPOSE} up -d --wait --timeout 30 --remove-orphans app-a
	# drain app-b
	${DOCKERCOMPOSE} run -q --remove-orphans admin cp docker/nginx/backend-configs/drain-b.conf /dynamic_config/nginx-backends.conf
	${DOCKERCOMPOSE} kill --remove-orphans -s SIGHUP nginx && sleep 2
	# restart app-b
	${DOCKERCOMPOSE} up -d --wait --timeout 30 --remove-orphans app-b
	# restore default config (using both app-a and app-b)
	${DOCKERCOMPOSE} run -q --remove-orphans admin cp docker/nginx/backend-configs/default.conf /dynamic_config/nginx-backends.conf
	${DOCKERCOMPOSE} kill --remove-orphans -s SIGHUP nginx

deploy:
	${DOCKERCOMPOSE} up -d --wait elasticsearch rabbitmq memcached  # get these (re)started first since other containers depend on them
	${DOCKERCOMPOSE} run manage collectstatic --no-input
	make rollout
	${DOCKERCOMPOSE} up -d --timeout 30 --remove-orphans 	# restart anything else that needs it

deploy-no-rollout:  # skips the smooth "rollout" in favour of a faster "up -d" with a few seconds of downtime
	${DOCKERCOMPOSE} up -d --wait elasticsearch rabbitmq memcached  # get these (re)started first since other containers depend on them
	${DOCKERCOMPOSE} run manage collectstatic --no-input
	${DOCKERCOMPOSE} up -d --timeout 30 --remove-orphans

new-code: build-code-containers deploy

new-code-pull: pull-build deploy

new-code-no-rollout: build-code-containers deploy-no-rollout

migrate-safe:
	${DOCKERCOMPOSE} up -d celery-batch  # make sure the relevant worker is up (so this can be done in 503 mode)
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
	${DOCKERCOMPOSE} stop `${DOCKERCOMPOSE} config --services | grep -e '^celery'` beat

rm503:
	${DOCKERCOMPOSE} run admin rm /dynamic_config/503
	${DOCKERCOMPOSE} up -d


# admin helpers

compose-yml:
	python manage.py build_compose_yml ALL
shell:
	${DOCKERCOMPOSE} run manage shell
dbshell:
	${DOCKERCOMPOSE} run manage dbshell
admin:
	${DOCKERCOMPOSE} run admin bash
