
# user who will be the effective operator (may repeat for others)
USERNAME=vagrant
USER_HOME=/home/${USERNAME}

# UID we use for files shared into docker containers, and owned by the service
COURSYS_USERNAME=coursys
COURSYS_UID=888
COURSYS_HOME=/home/${COURSYS_USERNAME}

SOURCE_LOCATION=/coursys
BRANCH=master
DATA_PREFIX=/data/

DOCKER_ARGS="--env-file ${SOURCE_LOCATION}/docker/demo.env -f ${SOURCE_LOCATION}/docker-compose-demo.yml"
