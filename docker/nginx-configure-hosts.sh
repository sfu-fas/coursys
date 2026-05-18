#!/bin/bash

set -e

cd /etc/nginx

for HOST in ${SERVE_HOSTS}
do
  echo -e "\n" >> /etc/nginx/conf.d/default.conf
  cat nginx-serve-host.conf | sed "s/DOMAIN_NAME/"${HOST}"/g" | sed "s/CANONICAL_NAME/"${CANONICAL_NAME}"/g" >> /etc/nginx/conf.d/default.conf
  echo -e "\n" >> /etc/nginx/conf.d/default.conf
done

for HOST in ${FORWARD_HOSTS}
do
  echo -e "\n" >> /etc/nginx/conf.d/default.conf
  cat nginx-forward-host.conf | sed "s/DOMAIN_NAME/"${HOST}"/g" | sed "s/CANONICAL_NAME/"${CANONICAL_NAME}"/g" >> /etc/nginx/conf.d/default.conf
  echo -e "\n" >> /etc/nginx/conf.d/default.conf
done
