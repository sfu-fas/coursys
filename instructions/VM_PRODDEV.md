# An Almost-Production Configuration with Vagrant and Virtualbox

In `courses/localsettings.py`

```py
DEPLOY_MODE = 'proddev'
# mail to a smtp4dev server: mail viewable at http://localhost:8025
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 2525
EMAIL_USE_SSL = False
```

In `courses/secrets.py`:
```py
RABBITMQ_PASSWORD = 'rabbitmq_password'
```

Make sure you have Vagrant and VirtualBox installed. Then,
```shell
cd deploy
vagrant up
```

Then to get into the VM,
```shell
vagrant ssh
```

Then in the VM, get things started with some test data.
```shell
cd /coursys/
echo "RABBITMQ_PASSWORD=rabbitmq_password" > .env
make proddev-start
make start-all
./manage.py migrate
python3 manage.py loaddata fixtures/*.json
python3 manage.py update_index
```

Head to http://localhost:8080/ and make sure things are working


