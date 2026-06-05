#!/bin/sh

source vars.sh

dnf -q upgrade -y
timedatectl set-timezone America/Vancouver

useradd --uid ${COURSYS_UID} --home-dir ${COURSYS_HOME} ${COURSYS_USERNAME}
install -o ${COURSYS_UID} -d /coursys 
