#!/bin/sh

# based on https://sfu.teamdynamix.com/TDClient/255/ITServices/KB/ArticleDet?ID=3932
set -e 

printf "Username: "
read USERNAME
stty -echo
printf "Password: "
read PASSWORD
stty echo
printf "\n"

cd /csrpt_auth

echo -n ${USERNAME} > username

{
  echo 'addent -password -p '${USERNAME}'@AD.SFU.CA -k 1 -e aes256-cts-hmac-sha1-96'
  sleep 0.5
  echo ${PASSWORD}
  echo 'addent -password -p '${USERNAME}'@AD.SFU.CA -k 1 -e aes128-cts-hmac-sha1-96'
  sleep 0.5
  echo ${PASSWORD}
  echo 'wkt adsfu.keytab'
} | ktutil
echo

/usr/bin/kinit `cat /csrpt_auth/username`@AD.SFU.CA -k -t /csrpt_auth/adsfu.keytab
