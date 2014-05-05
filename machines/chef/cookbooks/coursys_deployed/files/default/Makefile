restart:
	supervisorctl restart gunicorn

create_db:
	echo "no" | python manage.py syncdb && python manage.py migrate && python manage.py loaddata test_data

run:
	supervisord

