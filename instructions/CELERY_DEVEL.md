# Working with Celery

The system uses [Celery](http://www.celeryproject.org/) in several places for asynchronous and periodic tasks.

In production, it should Just Work (with the Chef recipe config). For development, the system should generally work fine without Celery: there is a setting `USE_CELERY` which is inspected to see if jobs should be fired asynchronously or not.

If you do need Celery for development, there are a couple of things to set up...

## Development-Mode Celery

In `courses/localsettings.py`, ask for Celery:
```
USE_CELERY = True
RABBITMQ_USER = 'guest'
RABBITMQ_HOSTPORT = 'localhost:5672'
RABBITMQ_VHOST = '/'
```

Celery (as we have configured it) uses AMQP implementation [RabbitMQ](https://www.rabbitmq.com/) as a message transport. It needs to be installed. In Ubuntu:
```
apt-get install rabbitmq-server
```

Then in `courses/secrets.py`:
```
RABBITMQ_PASSWORD = 'guest'
```

## RabbitMQ Docker

RabbitMQ can be started in a Docker container for development like:
```
docker run -d --hostname rabbitmq --name rabbitmq -p 5672:5672 rabbitmq:latest
# ...
docker container stop rabbitmq
docker container rm rabbitmq
```

## Starting a Worker

The workers in production are intricate, to handle concurrency and rate limiting just the right way. For development, you can likely start a single worker. If you have a virtualenv, the command will likely be:
```
../bin/celery -A courses worker -l INFO -B
```
