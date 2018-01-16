reload:
	killall -USR2 gunicorn

restart:
	sudo systemctl restart gunicorn

run:
	sudo systemctl start gunicorn

big-restart: restart
	sudo /etc/init.d/nginx reload
	sudo /etc/init.d/celeryd restart
	./manage.py collectstatic --noinput

pull:
	git pull

pull-restart: pull big-restart

chef:
	sudo chef-solo -c ~/courses/machines/chef/solo.rb -j ~/courses/machines/chef/run-list.json

check_things:
	LD_LIBRARY_PATH=/home/coursys/sqllib/lib64 ./manage.py check_things
