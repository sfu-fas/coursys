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

systemctl enable --now docker

echo 'alias dc="docker compose"' > /etc/profile.d/coursys.sh
echo 'export HOST_DOCKER_GID=`getent group docker | cut -d: -f3`' >> /etc/profile.d/coursys.sh
chmod 0644 /etc/profile.d/coursys.sh

# Put users into the docker group
setup_user_docker() {
  U=$1
  ( grep docker /etc/group | grep -q ${U} ) || gpasswd -a ${U} docker
}

setup_user_docker ${COURSYS_USERNAME}
setup_user_docker ${USERNAME}
