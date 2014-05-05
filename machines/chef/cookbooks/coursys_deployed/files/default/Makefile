restart:
	supervisorctl restart gunicorn

run:
	supervisord

big-restart: restart
	sudo /etc/init.d/celery restart
	sudo /etc/init.d/nginx reload

create_db:
	echo "no" | python manage.py syncdb && python manage.py migrate && python manage.py loaddata test_data

