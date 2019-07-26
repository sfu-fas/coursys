# Database Replication

A database read-only replica can be set up something like this..

Set up a VM somewhere and copy the Chef recipe over:
```bash
rsync -aP machines/chef/cookbooks/replica ubuntu@${REPLICA_SERVER}:
```

On the VM, get things ready and run the recipe to set everything up:
```bash
sudo apt install chef
sudo mkdir -p /var/chef/cookbooks/
sudo ln -sf /home/ubuntu/replica /var/chef/cookbooks/replica
sudo chef-solo -o replica
```

You should now be able to start up the containers that do the work: secure port forward, and local database.
```bash
docker-compose down; docker system prune -f
screen -S forwarder
./start-forward.sh
# ctrl-A d
screen -S db
./start-db.sh
# ctrl-A d
```

Get a [database snapshot where you noted the log position](https://dev.mysql.com/doc/refman/8.0/en/replication-howto-masterstatus.html). Copy it to `~/Private`:
```bash
rsync -aP database.dump.gz ubuntu@${REPLICA_SERVER}:Private/database.dump.gz
```
...and restore to the replica database:
```bash
pv Private/database.dump.gz | gunzip - | docker-compose run --rm forwarder ./mysql
```

Start replication on the slave by connecting:
```bash
docker-compose run --rm forwarder ./mysql
```
... and starting replication (adjusting values to reflect the log position of the data dump):
```sql
CHANGE MASTER TO
  MASTER_HOST='forwarder',
  MASTER_PORT=3333,
  MASTER_USER='username',
  MASTER_PASSWORD='password',
  MASTER_LOG_FILE='master-bin.000000',
  MASTER_LOG_POS=0;
START SLAVE;
SHOW SLAVE STATUS;
```
