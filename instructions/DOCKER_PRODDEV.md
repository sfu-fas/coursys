# An Almost-Production Configuration with Docker

You need Docker and Docker Compose first. On an Ubuntu-ish system, they can be installed like this:
```sh
sudo apt install docker-compose-v2 docker-buildx
```

Set up a proddev docker world:
```sh
ln -s compose-proddev.yml compose.yml  # or otherwise copy/link compose-proddev.yml to compose.yml
cp docker/app-config-template.toml secrets/app-config.toml
echo "rmqpass" > secrets/rabbitmq-default-password
make get-docker-rollout
```

Get things started:
```sh
docker compose pull
docker compose build
docker compose up -d mysql elasticsearch rabbitmq memcached
docker compose run manage collectstatic --no-input
docker compose run manage migrate
docker compose run manage loaddata fixtures/*
docker compose run manage update_index
docker compose up --remove-orphans -d
```

The system should be available in a few seconds at http://localhost:8080/

To update:
```sh
docker compose build
docker compose run manage collectstatic --no-input
docker compose up -d
```

To destroy:
```sh
docker compose stop
docker compose rm
docker system prune --volumes
#docker volume prune -a
```