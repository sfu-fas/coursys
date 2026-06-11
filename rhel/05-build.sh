#!/bin/sh

set -e
source ./config.sh

# get at least a template secrets/app-config.toml in place
[ -f ${SOURCE_LOCATION}/secrets/app-config.toml ] || install -o root -m 0644 ${SOURCE_LOCATION}/docker/app-config-template.toml ${SOURCE_LOCATION}/secrets/app-config.toml

# make sure the various data directories exist with the right ownership
install -o root -d ${DATA_PREFIX}nginx_logs
install -o ${COURSYS_USERNAME} -d ${DATA_PREFIX}submitted_files ${DATA_PREFIX}db_backups ${DATA_PREFIX}csrpt_auth ${DATA_PREFIX}dynamic_config
install -o 1000 -d ${DATA_PREFIX}elasticsearch7

# select out compose file as the default
cd ${SOURCE_LOCATION}
ln -sf ${DOCKER_COMPOSE_FILE} compose.yml

# actually build
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