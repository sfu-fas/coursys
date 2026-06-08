#!/bin/sh

set -e
source ./config.sh

install -o root -d ${DATA_PREFIX}rabbitmq3
install -o ${COURSYS_USERNAME} -d ${DATA_PREFIX}submitted_files ${DATA_PREFIX}db_backups ${DATA_PREFIX}csrpt_auth ${DATA_PREFIX}dynamic_config
install -o 101 -g 101 -d ${DATA_PREFIX}nginx_logs ${DATA_PREFIX}elasticsearch5

cd ${SOURCE_LOCATION}
ln -sf ${DOCKER_COMPOSE_FILE} compose.yml
docker compose pull
docker compose build --pull



# NGINX log rotation

# selinux permission for logrotate to touch that directory
[ -f /usr/bin/semanage ] || dnf install -y policycoreutils-python-utils
semanage fcontext -a -t var_log_t "${DATA_PREFIX}/nginx_logs"
restorecon -R ${DATA_PREFIX}/nginx_logs

# based on: https://alexanderzeitler.com/articles/rotating-nginx-logs-with-docker-compose/
cat <<EOF > /etc/logrotate.d/nginx-coursys
${DATA_PREFIX}/nginx_logs/*.log {
  daily
  missingok
  rotate 31
  dateext
  compress
  delaycompress
  notifempty
  sharedscripts
  postrotate
    cd ${SOURCE_LOCATION} && docker compose kill -s USR1 nginx
  endscript
}
EOF

systemctl restart logrotate