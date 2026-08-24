#!/bin/bash

# based on https://sfu.teamdynamix.com/TDClient/255/ITServices/KB/ArticleDet?ID=3932
set -e

printf "Username: "
read USERNAME
stty -echo
printf "Password: "
read PASSWORD
stty echo
printf "\n"

echo -n ${USERNAME} > /csrpt_auth/username

rm /tmp/krb5cc_${UID}
{
  echo 'addent -password -p '${USERNAME}'@AD.SFU.CA -k 1 -e aes256-cts-hmac-sha1-96'
  sleep 0.5
  echo ${PASSWORD}
  echo 'addent -password -p '${USERNAME}'@AD.SFU.CA -k 1 -e aes128-cts-hmac-sha1-96'
  sleep 0.5
  echo ${PASSWORD}
  echo 'wkt /csrpt_auth/adsfu.keytab'
} | ktutil
echo

./kinit-refresh.sh
