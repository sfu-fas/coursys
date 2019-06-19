FROM compose_app:latest

CMD /wait db 3306 && /usr/local/bin/celery worker -A courses -l INFO -B