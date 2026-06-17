#!/bin/bash

# installation of docker tools

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

# Get docker-rollout
[ -f /usr/bin/docker ] || dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
mkdir -p /usr/local/lib/docker/cli-plugins
[ -f /usr/local/lib/docker/cli-plugins/docker-rollout ] || curl -L https://github.com/wowu/docker-rollout/releases/download/v0.13/docker-rollout > /usr/local/lib/docker/cli-plugins/docker-rollout
chmod +x /usr/local/lib/docker/cli-plugins/docker-rollout

systemctl enable --now docker

# Put users into the docker group
setup_user_docker() {
  U=$1
  ( grep docker /etc/group | grep -q ${U} ) || gpasswd -a ${U} docker
}

setup_user_docker ${COURSYS_USERNAME}
setup_user_docker ${USERNAME}
