#!/bin/bash

source vars.sh
source /etc/os-release

# cat <<EOF > /etc/docker/daemon.json
# {
#   "log-driver": "syslog",
#   "bip": "10.131.0.1/16",
#   "fixed-cidr": "10.131.0.0/17",
#   "default-address-pools":[
#       {"base":"10.132.0.0/16","size":24}
#   ],
#   "proxies": {
#    "http-proxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
#    "https-proxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
#    "no-proxy": "cas.sfu.ca,.sfu.ca,localhost"
#   }
# }
# EOF

[ -f /usr/share/man/man8/dnf4-config-manager.8.gz ] || dnf install -y dnf-plugins-core

if [ ${ID} == rhel ] ; then
    DNF_ADD="dnf config-manager --add-repo"
else
    DNF_ADD="dnf config-manager addrepo --from-repofile"
fi
[ -f /etc/yum.repos.d/docker-ce.repo ] || ( ${DNF_ADD} https://download.docker.com/linux/${ID}/docker-ce.repo )

[ -f /usr/bin/docker ] || dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sed -i '/^\[Service\]/a Environment="HTTP_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"\nEnvironment="HTTPS_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"\nEnvironment="NO_PROXY=localhost,.sfu.ca,*.sfu.ca"' /usr/lib/systemd/system/docker.service
systemctl daemon-reload

systemctl enable --now docker

gpasswd -a ${USERNAME} docker
install -o ${COURSYS_USERNAME} -d ${COURSYS_HOME}/.docker

echo <<EOF >> ${COURSYS_HOME}/.docker/config.json
{
  "proxies": {
    "httpProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
    "httpsProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
    "noProxy": "cas.sfu.ca,.sfu.ca,localhost"
   }
}
EOF


( grep docker /etc/group | grep -q ${COURSYS_USERNAME} ) || gpasswd -a ${COURSYS_USERNAME} docker

install -o ${USERNAME} -d ${USER_HOME}/.docker
echo <<EOF >> ${COURSYS_HOME}/.docker/config.json
{
  "proxies": {
    "httpProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
    "httpsProxy": "http://bby-vcontrol-proxy.its.sfu.ca:8080",
    "noProxy": "cas.sfu.ca,.sfu.ca,localhost"
   }
}
EOF
[ -f ${USER_HOME}/.docker/cli-plugins/docker-rollout ] || \
    ( mkdir -p ${USER_HOME}/.docker/cli-plugins \
    && curl https://github.com/wowu/docker-rollout/releases/download/v0.13/docker-rollout -o ${USER_HOME}/.docker/cli-plugins/docker-rollout \
    && chmod +x ${USER_HOME}/.docker/cli-plugins/docker-rollout && chown -R ${USERNAME} ${USER_HOME}/.docker )


