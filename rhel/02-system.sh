#!/bin/sh

# Basic setup for the OS

set -e
source ./config.sh

dnf -q upgrade -y
timedatectl set-timezone America/Vancouver
[ -f /usr/bin/wget ] || dnf install -y wget

grep -qe "^${COURSYS_USERNAME}:" /etc/passwd || useradd --uid ${COURSYS_UID} --home-dir ${COURSYS_HOME} ${COURSYS_USERNAME}
install -o ${COURSYS_UID} -d ${SOURCE_LOCATION}

[ -f ${SOURCE_LOCATION}/manage.py ] || (\
  git clone https://github.com/sfu-fas/coursys.git -b ${BRANCH} ${SOURCE_LOCATION} \
  && chown -R ${COURSYS_USERNAME} ${SOURCE_LOCATION} )

# convenience utils
[ -f /usr/bin/lsof ] || dnf install -y lsof
[ -f /usr/bin/make ] || dnf install -y make
