# An Almost-Production Configuration with Vagrant and Virtualbox

Make sure you have [VirtualBox](https://www.virtualbox.org/) and [Vagrant](http://vagrantup.com/) installed. Then,
```shell
cd deploy
vagrant up
```

Then to get into the VM,
```shell
vagrant ssh
```

Then in the VM, get appropriate configuration in place. That is likely something like this:
```shell
cd /coursys/
echo -e "DEPLOY_MODE = 'proddev'\nEMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'\nEMAIL_HOST = 'localhost'\nEMAIL_PORT = 2525\nEMAIL_USE_SSL = False\nMOSS_DISTRIBUTION_PATH = '/home/vagrant/moss'\nCSRF_TRUSTED_ORIGINS = ['http://localhost:8080']" | sudo tee courses/localsettings.py
echo -e "RABBITMQ_PASSWORD = 'rabbitmq_password'" | sudo tee courses/secrets.py
```

Then, get things started with some test data:
```shell
cd /coursys/
make proddev-start
sleep 10  # for mysql to actually get started
python3 manage.py migrate
make start-all
python3 manage.py loaddata fixtures/*.json
python3 manage.py update_index
make restart-all
```

In theory, should be able to access http://localhost:8080/ for the site, and http://localhost:8025/ for the development email.
Have a look at the admin panel deployment checks to see what's up http://localhost:8080/sysadmin/panel but note that
it's expected that the reporting database and external APIs won't work in this environment.

There is more information on the actual production deployment in `deployment/README.md`.
