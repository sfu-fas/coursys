#!/bin/bash

set -e
USERNAME=coursys
USER_UID=888
USER_HOME=/home/${USERNAME}

# In a Vagrant VM, consider:
# sudo parted /dev/sda "resizepart 3 100%"
# sudo btrfs filesystem resize max /

yum -q upgrade -y

#dnf install -y dnf-plugins-core
(dnf repolist | grep -q "^docker-ce-stable ") || dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

timedatectl set-timezone America/Vancouver
#[ -f /usr/bin/pip3 ] || yum install -y python3-pip
[ -f /usr/bin/git ] || dnf install -y git
[ -f /usr/bin/docker ] || dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
#[ -f /usr/bin/mariadb ] || yum install -y mariadb-client-utils
#[ -f /usr/bin/nginx ] || yum install -y nginx

( grep -q -e "^coursys:" /etc/passwd ) || useradd -s /bin/bash --uid ${USER_UID} coursys

#systemctl enable --now nginx
systemctl enable --now docker
( grep docker /etc/group | grep -q ${USERNAME} ) || gpasswd -a ${USERNAME} docker

[ -f ${USER_HOME}/.docker/cli-plugins/docker-rollout ] || (mkdir -p ${USER_HOME}/.docker/cli-plugins && curl https://github.com/wowu/docker-rollout/releases/download/v0.13/docker-rollout -o ${USER_HOME}/.docker/cli-plugins/docker-rollout && chmod +x ${USER_HOME}/.docker/cli-plugins/docker-rollout)

#[ -f /usr/bin/tsql ] || yum install -y freetds

#PYTHON=python3
#VIRTUALENV='/venv'
#PYTHON_VERSION=$(${PYTHON} -c "import sys; print('%i.%i' % (sys.version_info.major, sys.version_info.minor))")
#PYTHON_BIN_DIR=${VIRTUALENV}/bin/
#PYTHON_LIB_DIR=${VIRTUALENV}/lib/python${PYTHON_VERSION}/dist-packages
#echo $PYTHON_LIB_DIR