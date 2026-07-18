#!/bin/bash

# Production-server-only setup

set -e
source ./config.sh

grep -q "umask 022" /etc/profile || echo "umask 022" >> /etc/profile
echo 'Defaults:%scs-cloud-coursys-servers-priv-pam  env_keep += "HTTP_PROXY HTTPS_PROXY NO_PROXY"' > /etc/sudoers.d/coursys
chmod 0644 /etc/sudoers.d/coursys

# Rationalle for the daemon.json contents...
# * Limit the size of the log files. (Docker logs may be useful to diagnose problems, but shouldn't be needed long-term.)
# * Ensure that Docker's internal IP addresses don't conflict with the data centre's internal address range.
# * Let Docker builds do outside web requests.

cat <<EOF > /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  },
  "bip": "10.131.0.1/16",
  "fixed-cidr": "10.131.0.0/17",
  "default-address-pools":[
      {"base":"10.132.0.0/16","size":24}
  ],
  "proxies": {
   "http-proxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
   "https-proxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
   "no-proxy": "cas.sfu.ca,.sfu.ca,localhost"
  }
}
EOF

# Insert HTTP_PROXY environment variables for the docker service.
# (It's a mystery to me why the daemon.json doesn't take care of this, but it apparently doesn't.)
DOCKER_SERVICE=/usr/lib/systemd/system/docker.service
grep -q HTTP_PROXY ${DOCKER_SERVICE} || sed -i '/^\[Service\]/a Environment="HTTP_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"\nEnvironment="HTTPS_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"\nEnvironment="NO_PROXY=localhost,.sfu.ca,*.sfu.ca"'  ${DOCKER_SERVICE}
systemctl daemon-reload
systemctl reload docker

# User setup for Docker
cat <<EOF > /tmp/config.json
{
  "proxies": {
    "default": {
      "httpProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
      "httpsProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
      "noProxy": "cas.sfu.ca,.sfu.ca,localhost"
    }
  }
}
EOF

setup_user_docker_production() {
  U=$1
  H=$2
  mkdir -p ${H}/.docker
  cp /tmp/config.json ${H}/.docker/config.json
  chown -R $U ${H}/.docker
}

setup_user_docker_production ${COURSYS_USERNAME} ${COURSYS_HOME}
setup_user_docker_production ${USERNAME} ${USER_HOME}
setup_user_docker_production root /root
