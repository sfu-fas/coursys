devel-runserver:
	python3 manage.py runserver 0:8000
devel-celery:
	celery -A courses -l INFO worker -B

proddev-start-all:
	sudo systemctl start nginx
	docker-compose -f docker-compose.yml -f docker-compose-proddev.yml up -d
	sudo systemctl start gunicorn
	sudo systemctl start celery
	sudo systemctl start celerybeat
proddev-restart-all:
	docker-compose -f docker-compose.yml -f docker-compose-proddev.yml restart
	sudo systemctl restart gunicorn
	sudo systemctl restart celery
	sudo systemctl restart celerybeat
	sudo systemctl restart nginx
proddev-stop-all:
	docker-compose -f docker-compose.yml -f docker-compose-proddev.yml stop
	sudo systemctl stop gunicorn
	sudo systemctl stop celery
	sudo systemctl stop celerybeat
	sudo systemctl stop nginx
proddev-rm-all:
	docker-compose -f docker-compose.yml -f docker-compose-proddev.yml rm

start-all:
	sudo systemctl start nginx
	docker-compose up -d
	sudo systemctl start gunicorn
	sudo systemctl start celery
	sudo systemctl start celerybeat
restart-all:
	docker-compose restart
	sudo systemctl restart gunicorn
	sudo systemctl restart celery
	sudo systemctl restart celerybeat
	sudo systemctl restart nginx

new-code:
	sudo systemctl reload gunicorn
	sudo systemctl reload celery
	sudo systemctl restart celerybeat

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
	cd ${COURSYS_DIR} && npm install
	cd ${COURSYS_DIR} && python3 manage.py collectstatic --no-input

rebuild-hardcore:
	sudo systemctl daemon-reload
	sudo systemctl stop ntp && sudo ntpdate pool.ntp.org && sudo systemctl start ntp
	cd ${COURSYS_DIR} && docker-compose pull
	touch ${COURSYS_DIR}/503
	cd ${COURSYS_DIR} && docker-compose restart
	rm -rf ${COURSYS_STATIC_DIR}/static
	make rebuild
	rm ${COURSYS_DIR}/503
	docker system prune -f
