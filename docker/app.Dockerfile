ARG PYTHON_MINOR_VERSION=3.13

# builder that can collect the python and node dependencies

FROM python:${PYTHON_MINOR_VERSION}-slim AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    git locales-all npm libfreetype-dev \
    pkg-config default-libmysqlclient-dev build-essential \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /coursys /build
WORKDIR /build

COPY package.json /build/package.json
COPY package-lock.json /build/package-lock.json
RUN npm ci

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt /build/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /build/requirements.txt



# base image: common config to both the web app and celery workers (i.e. most congig)

FROM python:${PYTHON_MINOR_VERSION}-slim AS base

# packages groups here: basics; csrpt connection; admin helpers
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    locales-all default-mysql-client \
    unixodbc-dev krb5-user tdsodbc \
    curl wget freetds-bin \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

#COPY docker/files/odbc.ini /etc/odbc.ini
COPY docker/files/krb5.conf /etc/krb5.conf
#COPY docker/files/odbcinst.ini /etc/odbcinst.ini

ARG PYTHON_MINOR_VERSION
ARG DEPLOY_MODE
ENV DEPLOY_MODE=${DEPLOY_MODE}
ENV LANG=en_CA.UTF-8
ENV IN_DOCKER=yes
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /coursys
WORKDIR /coursys

ARG UID=888
RUN useradd -l -s /bin/bash --uid ${UID} -d /home/coursys coursys \
  && install -o ${UID} -d /static /csrpt_auth /db_backups /submitted_files /dynamic_config

COPY --exclude=.git --exclude=node_modules --exclude=secrets --exclude=docker --exclude=*.yml --exclude=instructions \
  --exclude=submitted_files --exclude=whoosh_index --exclude=deploy --exclude=rhel \
  . /coursys
COPY courses/docker-localsettings-${DEPLOY_MODE}.py /coursys/courses/localsettings.py

COPY --from=builder /build/node_modules /build/node_modules
COPY --from=builder /usr/local/lib/python${PYTHON_MINOR_VERSION}/site-packages/ /usr/local/lib/python${PYTHON_MINOR_VERSION}/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

USER coursys
RUN ln -sf /csrpt_auth/krb5cc /tmp/krb5cc_${UID}  # do this with coursys user ownership
RUN test -r ./manage.py  # check that file permissions are sane in the container: if this fails, check file permissions in the source directory
RUN echo "" | python -m unidecode  # make sure our modules are there: failure points to a problem in the COPY site-packages



# app image: process for actually handling web requests

FROM base AS app

COPY docker/files/gunicorn-worker.sh /gunicorn-worker.sh
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
  CMD curl --fail http://localhost:8000/healthcheck || exit 1
CMD ["/gunicorn-worker.sh"]



# celery image: config for celery workers

FROM base AS celery

COPY docker/files/celery-worker.sh /celery-worker.sh
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl --fail http://localhost:9000/ || exit 1
ARG QUEUE
ARG CONCURRENCY
ENV QUEUE=${QUEUE}
ENV CONCURRENCY=${CONCURRENCY}
CMD ["/celery-worker.sh"]



# celery beat image

FROM base AS beat
CMD ["celery", "-A", "courses", "beat", "--loglevel", "INFO"]



# django manage helper

FROM base AS manage
ENTRYPOINT ["python", "/coursys/manage.py"]
CMD ["shell"]



# sysadmin helper

FROM base AS admin
USER root
RUN install -o coursys -d /home/coursys
USER coursys
CMD ["bash"]
