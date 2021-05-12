SYSTEMCTL=sudo systemctl
SUCOURSYS=sudo -E -u ${COURSYS_USER} HOME=${COURSYS_USER_HOME}
DOCKERCOMPOSE=${SUCOURSYS} docker-compose

# For local development

devel-runserver:
	python3 manage.py runserver 0:8000
devel-celery:
	celery -A courses -l INFO worker -B

# For production-like development (possibly in a VM)

proddev-start-all:
	${SYSTEMCTL} start nginx
	${DOCKERCOMPOSE} -f docker-compose.yml -f docker-compose-proddev.yml up -d
	${SYSTEMCTL} start gunicorn
	${SYSTEMCTL} start celery
	${SYSTEMCTL} start celerybeat
proddev-restart-all:
	${DOCKERCOMPOSE} -f docker-compose.yml -f docker-compose-proddev.yml restart
	${SYSTEMCTL} restart gunicorn
	${SYSTEMCTL} restart celery
	${SYSTEMCTL} restart celerybeat
	${SYSTEMCTL} restart nginx
proddev-stop-all:
	${DOCKERCOMPOSE} -f docker-compose.yml -f docker-compose-proddev.yml stop
	${SYSTEMCTL} stop gunicorn
	${SYSTEMCTL} stop celery
	${SYSTEMCTL} stop celerybeat
	${SYSTEMCTL} stop nginx
proddev-rm-all:
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
	${SUCOURSYS} cp deploy/run-list-production.json deploy/run-list-production.bak
	${SUCOURSYS} git checkout -- deploy/run-list-production.json
	${SUCOURSYS} git pull
	${SUCOURSYS} cp deploy/run-list-production.bak deploy/run-list-production.json

# New code/configuration tasks

new-code:
	${SYSTEMCTL} reload gunicorn
	${SYSTEMCTL} restart celery
	${SYSTEMCTL} restart celerybeat

new-code-static:
	${SUCOURSYS} npm install
	${SUCOURSYS} python3 manage.py collectstatic --no-input
	make new-code

migrate-safe:
	${SUCOURSYS} python3 manage.py backup_db
	${SUCOURSYS} python3 manage.py migrate
	${SUCOURSYS} python3 manage.py backup_db

503:
	${SUCOURSYS} touch ${COURSYS_DIR}/503
rm503:
	${SUCOURSYS} rm ${COURSYS_DIR}/503

rebuild:
	sudo apt update && sudo apt upgrade
	sudo pip3 install -r ${COURSYS_DIR}/requirements.txt
	cd ${COURSYS_DIR} && ${SUCOURSYS} npm install
	cd ${COURSYS_DIR} && ${SUCOURSYS} python3 manage.py collectstatic --no-input

rebuild-hardcore:
	${SYSTEMCTL} daemon-reload
	${SYSTEMCTL} stop ntp && sudo ntpdate pool.ntp.org && ${SYSTEMCTL} start ntp
	cd ${COURSYS_DIR} && ${DOCKERCOMPOSE} pull
	make 503
	cd ${COURSYS_DIR} && ${DOCKERCOMPOSE} restart
	${SUCOURSYS} rm -rf ${COURSYS_STATIC_DIR}/static
	make rebuild
	make rm503
	${SUCOURSYS} docker system prune -f

production-chef:
	cd ${COURSYS_DIR} && sudo chef-solo -c ./deploy/solo.rb -j ./deploy/run-list-production.json

# Utility helpers

manage: # used like: "make manage ARGS=shell"
	${SUCOURSYS} python3 manage.py $(ARGS)
shell:
	${SUCOURSYS} python3 manage.py shell
dbshell:
	${SUCOURSYS} python3 manage.py dbshell
