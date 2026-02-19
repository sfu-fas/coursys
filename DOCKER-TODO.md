* kinit auth piped in somehow
* submission dir
* DB backup dir
* moss distribution
* redirect vs serve hosts in nginx


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
```


## Swarm Notes

```sh
docker swarm init --advertise-addr 10.0.0.2
```