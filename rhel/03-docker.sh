#!/bin/bash

set -e
source /etc/os-release  # for distribution $ID variable
source config.sh


[ -f /usr/share/man/man8/dnf4-config-manager.8.gz ] || dnf install -y dnf-plugins-core

if [ ${ID} == rhel ] ; then
    DNF_ADD="dnf config-manager --add-repo"
else
    DNF_ADD="dnf config-manager addrepo --from-repofile"
fi
[ -f /etc/yum.repos.d/docker-ce.repo ] || ( ${DNF_ADD} https://download.docker.com/linux/${ID}/docker-ce.repo )

[ -f /usr/bin/docker ] || dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

setup_user_docker() {
  U=$1
  H=$2
  ( grep docker /etc/group | grep -q ${U} ) || gpasswd -a ${U} docker
  install -o ${U} -d ${H}/.docker
  [ -f ${H}/.docker/cli-plugins/docker-rollout ] || \
      ( mkdir -p ${H}/.docker/cli-plugins \
      && wget https://github.com/wowu/docker-rollout/releases/download/v0.13/docker-rollout -O ${H}/.docker/cli-plugins/docker-rollout \
      && chmod +x ${H}/.docker/cli-plugins/docker-rollout && chown -R ${U} ${H}/.docker )
}

setup_user_docker ${COURSYS_USERNAME} ${COURSYS_HOME}
setup_user_docker ${USERNAME} ${USER_HOME}

[ -f /usr/bin/semanage ] || dnf install -y policycoreutils-python-utils
semanage fcontext -a -t var_log_t "${DATA_PREFIX}/nginx_logs"
restorecon -R ${DATA_PREFIX}/nginx_logs

# nginx log rotation based on: https://alexanderzeitler.com/articles/rotating-nginx-logs-with-docker-compose/
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