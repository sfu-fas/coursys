SYSTEMCTL=sudo systemctl
SUCOURSYS=sudo -E -u ${COURSYS_USER} HOME=${COURSYS_USER_HOME}
DOCKERCOMPOSE=${SUCOURSYS} docker-compose

# For local development

devel-runserver:
	python3 manage.py runserver 0:8000
devel-celery:
	celery -A courses -l INFO worker -B

# For production-like development (possibly in a VM)

proddev-start:
	test `hostname` != 'coursys' && test ${COURSYS_DEPLOY_MODE} != 'production'
	${DOCKERCOMPOSE} -f docker-compose-proddev.yml up -d
proddev-restart:
	test `hostname` != 'coursys' && test ${COURSYS_DEPLOY_MODE} != 'production'
	${DOCKERCOMPOSE} -f docker-compose-proddev.yml restart
proddev-stop:
	test `hostname` != 'coursys' && test ${COURSYS_DEPLOY_MODE} != 'production'
	${DOCKERCOMPOSE} -f docker-compose-proddev.yml stop
proddev-rm-all:
	test `hostname` != 'coursys' && test ${COURSYS_DEPLOY_MODE} != 'production'
	${DOCKERCOMPOSE} -f docker-compose.yml -f docker-compose-proddev.yml rm

# Production server tasks

start-all:
	${SYSTEMCTL} start nginx
	${DOCKERCOMPOSE} up -d
	${SYSTEMCTL} start gunicorn
	${SYSTEMCTL} start celery
	${SYSTEMCTL} start celerybeat
restart-all:
	${DOCKERCOMPOSE} restart
	${SYSTEMCTL} restart gunicorn
	${SYSTEMCTL} restart celery
	${SYSTEMCTL} restart celerybeat
	${SYSTEMCTL} restart nginx

pull:
	${SUCOURSYS} git pull

# New code/configuration tasks

new-code-lite:
	${SYSTEMCTL} reload gunicorn
	${SYSTEMCTL} restart celery
	${SYSTEMCTL} restart celerybeat

new-code:
	${SUCOURSYS} npm install
	${SUCOURSYS} python3 manage.py collectstatic --no-input
	make new-code-lite

clear-cache:
	${SUCOURSYS} docker-compose restart memcached

migrate-safe:
	${SUCOURSYS} python3 manage.py backup_db
	${SUCOURSYS} python3 manage.py migrate
	${SUCOURSYS} python3 manage.py backup_db

503:
	${SUCOURSYS} touch ${COURSYS_DIR}/503
	${SYSTEMCTL} stop celery
	${SYSTEMCTL} stop celerybeat
rm503:
	${SUCOURSYS} rm ${COURSYS_DIR}/503
	${SYSTEMCTL} start celery
	${SYSTEMCTL} start celerybeat

rebuild:
	sudo apt update && sudo apt upgrade
	sudo pip3 install -r ${COURSYS_DIR}/requirements.txt
	${DOCKERCOMPOSE} build --pull
	make new-code

rebuild-hardcore:
	#make chef
	${SYSTEMCTL} daemon-reload # catches any changed service definitions
	${SYSTEMCTL} stop ntp && sudo ntpdate pool.ntp.org && ${SYSTEMCTL} start ntp
	${DOCKERCOMPOSE} pull
	make 503
	${DOCKERCOMPOSE} restart
	${SUCOURSYS} rm -rf ${COURSYS_STATIC_DIR}/static # to clear out any orphaned static files and freshen: must purge memcached around the same time so compressor knows to look for changes
	make rebuild
	make rm503
	${SUCOURSYS} docker system prune -f # clear any orphaned docker images/containers

chef:
	sudo chef-solo -c ./deploy/solo.rb -j ./deploy/run-list.json

# Utility helpers

manage: # used like: "make manage ARGS=shell"
	${SUCOURSYS} python3 manage.py $(ARGS)
shell:
	${SUCOURSYS} python3 manage.py shell
dbshell:
	${SUCOURSYS} python3 manage.py dbshell
backup_db:
	${SUCOURSYS} python3 manage.py backup_db
