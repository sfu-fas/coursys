#!/bin/bash

# get the username and password
read -p "Username: " USER
#read -p "Username: " USER
stty -echo; read -p "Password: " PW; echo; stty echo

NL="$(printf '%b' '\015')" # newline character
SESSION=reportingDB

# if no reportingDB screen session exists, create one in background
screen -ls | grep -q ${SESSION} \
  || screen -d -m -S ${SESSION}

# inject the username/password into environment variables in the session
screen -S ${SESSION} -X stuff ${NL}
screen -S ${SESSION} -X stuff 'USER='${USER}${NL}
# the following prevents passwd from being visible on-screen
screen -S ${SESSION} -X stuff 'stty -echo; read -p "Password: " PW; echo; stty echo'${NL} 
sleep 0.1
screen -S ${SESSION} -X stuff ${PW}${NL}
screen -S ${SESSION} -X stuff "export USER"${NL}
screen -S ${SESSION} -X stuff "export PW"${NL}

screen -S ${SESSION} -X stuff "python ~/courses/server-setup/reporting.py"

