#!/bin/bash

# Production-server-only setup

set -e
source ./config.sh

#   "log-driver": "syslog",
#   "bip": "10.131.0.1/16",
#   "fixed-cidr": "10.131.0.0/17",
#   "default-address-pools":[
#       {"base":"10.132.0.0/16","size":24}
#   ],


cat <<EOF > /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  },
  "proxies": {
   "http-proxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
   "https-proxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
   "no-proxy": "cas.sfu.ca,.sfu.ca,localhost"
  }
}
EOF

DOCKER_SERVICE=/usr/lib/systemd/system/docker.service
grep -q HTTP_PROXY ${DOCKER_SERVICE} || sed -i '/^\[Service\]/a Environment="HTTP_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"\nEnvironment="HTTPS_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"\nEnvironment="NO_PROXY=localhost,.sfu.ca,*.sfu.ca"'  ${DOCKER_SERVICE}
systemctl daemon-reload
systemctl reload docker

echo -e '{ "proxies": { "default": {\n"httpProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",\n"httpsProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",\n"noProxy": "cas.sfu.ca,.sfu.ca,localhost"\n}}}' > /tmp/config.json
setup_user_docker_production() {
  U=$1
  H=$2
  cp /tmp/config.json ${H}/.docker/config.json
  chown $U ${H}/.docker/config.json
}

setup_user_docker_production ${COURSYS_USERNAME} ${COURSYS_HOME}
setup_user_docker_production ${USERNAME} ${USER_HOME}
setup_user_docker_production root /root
