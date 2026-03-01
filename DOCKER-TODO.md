* kinit auth piped in somehow
* submission dir
* DB backup dir
* maintenance mode/503 handling
* logrotate


## Compose Notes

For mostly-production-like like deployment:
```sh
docker compose -f docker-compose-demo.yml build
docker compose -f docker-compose-demo.yml up -d
docker compose -f docker-compose-demo.yml run app ./manage.py migrate
docker compose -f docker-compose-demo.yml run app ./manage.py collectstatic --no-input
docker compose -f docker-compose-demo.yml run app ./manage.py loaddata fixtures/*
docker compose -f docker-compose-demo.yml run app ./manage.py update_index
docker compose -f docker-compose-demo.yml up --remove-orphans -d
```

To destroy:
```sh
docker compose -f docker-compose-demo.yml stop
docker compose -f docker-compose-demo.yml rm
docker system prune
```


## Swarm Notes

I'm probably going to leave well enough alone and just use compose, but for the record...

```sh
docker swarm init --advertise-addr 10.0.0.2
docker stack deploy -c docker-compose-registry.yml registry
docker compose -f docker-compose-demo.yml build
docker compose -f docker-compose-demo.yml push
docker stack deploy -c docker-compose-demo.yml coursys
```

```sh
docker exec $(docker ps -q -f name=coursys_app | head -n1) ./manage.py migrate
docker exec $(docker ps -q -f name=coursys_app | head -n1) ./manage.py collectstatic --no-input
docker exec $(docker ps -q -f name=coursys_app | head -n1) ./manage.py loaddata fixtures/*
docker exec $(docker ps -q -f name=coursys_app | head -n1) ./manage.py update_index
```

```sh
docker service ls
```
