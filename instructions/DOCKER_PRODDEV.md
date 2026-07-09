# An Almost-Production Configuration with Docker

You need Docker and Docker Compose first. On an Ubuntu-ish system, they can be installed like this:
```sh
sudo apt install docker-compose-v2 docker-buildx
```

Set up a proddev docker world:
```sh
ln -s compose-proddev.yml compose.yml  # or otherwise copy/link compose-proddev.yml to compose.yml
cp secrets/app-config-template.toml secrets/app-config.toml
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


## On Windows

It should be possible to do all of this in Windows. Some notes...

First, install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/).

I used the [git shell for Windows](https://git-scm.com/install/windows) to run the above commands,
but any way you can get `docker compose` to run should work. The git shell was mangling the line
endings of the source files and I had to do this to stop it:
```shell
git config --global core.autocrlf false
```