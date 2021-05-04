SYSTEMCTL="sudo systemctl"
SUCOURSYS="sudo -E -u ${COURSYS_USER}"
DOCKERCOMPOSE="${SUCOURSYS} docker-compose"

devel-runserver:
	python3 manage.py runserver 0:8000
devel-celery:
	celery -A courses -l INFO worker -B

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

new-code:
	${SYSTEMCTL} reload gunicorn
	${SYSTEMCTL} reload celery
	${SYSTEMCTL} restart celerybeat

new-code-static:
	npm install
	python3 manage.py collectstatic --no-input
	make new-code

migrate-safe:
	python3 manage.py backup_db
	python3 manage.py migrate
	python3 manage.py backup_db

rebuild:
	sudo apt update && sudo apt upgrade
	sudo pip3 install -r ${COURSYS_DIR}/requirements.txt
	cd ${COURSYS_DIR} && ${SUCOURSYS} npm install
	cd ${COURSYS_DIR} && ${SUCOURSYS} python3 manage.py collectstatic --no-input

rebuild-hardcore:
	${SYSTEMCTL} daemon-reload
	${SYSTEMCTL} stop ntp && sudo ntpdate pool.ntp.org && ${SYSTEMCTL} start ntp
	cd ${COURSYS_DIR} && ${DOCKERCOMPOSE} pull
	${SUCOURSYS} touch ${COURSYS_DIR}/503
	cd ${COURSYS_DIR} && ${DOCKERCOMPOSE} restart
	${SUCOURSYS} rm -rf ${COURSYS_STATIC_DIR}/static
	make rebuild
	${SUCOURSYS} rm ${COURSYS_DIR}/503
	${SUCOURSYS} docker system prune -f
