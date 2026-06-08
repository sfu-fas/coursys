# An Almost-Production Configuration with Docker

Set up a proddev docker world:
```sh
ln -s compose-proddev.yml compose.yml
sudo install -o 888 -d data/submitted_files data/db_backups
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