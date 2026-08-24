This directory is intended for files that will piped into docker container as secrets (i.e. in /run/secrets/*).

* `app-config.toml`: All secrets and local config needed by the Django code. See `app-config-template.toml` for the format.
* `rabbitmq-default-password`: RabbitMQ password. Plain text: `echo "rmqpass" > secrets/rabbitmq-default-password`. Optional: RABBITMQ_DEFAULT_PASS will be used if the secret file isn't in the image.
