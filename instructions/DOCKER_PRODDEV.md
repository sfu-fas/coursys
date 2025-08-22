# An Almost-Production Configuration with Docker

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


Get the Docker-based things up and running:
```sh
export RABBITMQ_PASSWORD=rabbitmq_password
docker compose -f docker-compose.yml -f docker-compose-proddev.yml pull
docker compose -f docker-compose.yml -f docker-compose-proddev.yml build --pull
docker compose -f docker-compose.yml -f docker-compose-proddev.yml up -d
```

Basic setup as necessary: activate a virtualenv and,
```sh
pip install -r requirements.txt
npm install
python3 manage.py migrate
python3 manage.py loaddata fixtures/*.json
python3 manage.py update_index
sudo mkdir -p /data/submitted_files
sudo chown $USER /data/submitted_files
```

In one terminal, start Celery:
```sh
../bin/celery -A courses worker -l INFO -B
```

In another, start a Django dev server:
```sh
python3 manage.py runserver
```

## Shutting Down

```shell
docker compose -f docker-compose.yml -f docker-compose-proddev.yml stop
docker compose -f docker-compose.yml -f docker-compose-proddev.yml rm
# sudo rm -rf /data/*
```
