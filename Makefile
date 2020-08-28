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

new-code:
	sudo systemctl reload gunicorn
	sudo systemctl reload celery
	sudo systemctl restart celerybeat

new-code-static:
	cd ${COURSYS_DIR} && npm install
	cd ${COURSYS_DIR} && python3 manage.py collectstatic --no-input
	make new-code

rebuild:
	sudo apt update && sudo apt upgrade
	sudo pip3 install -r ${COURSYS_DIR}/requirements.txt
	cd ${COURSYS_DIR} && npm install
	cd ${COURSYS_DIR} && python3 manage.py collectstatic --no-input

rebuild-hardcore:
	touch ${COURSYS_DIR}/503
	sudo systemctl stop ntp && sudo ntpdate pool.ntp.org && sudo systemctl start ntp
	cd ${COURSYS_DIR} && docker-compose pull && docker-compose restart
	docker system prune -f
	rm -rf ${COURSYS_STATIC_DIR}/static
	make rebuild
	rm ${COURSYS_DIR}/503
