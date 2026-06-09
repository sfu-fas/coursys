# base image: common config to both the web app and celery workers (i.e. most congig)

FROM python:3.13 AS base

RUN apt-get update \
  && apt-get install -y locales-all npm libfreetype-dev default-mysql-client \
    unixodbc-dev krb5-user tdsodbc \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

#COPY docker/files/odbc.ini /etc/odbc.ini
COPY docker/files/krb5.conf /etc/krb5.conf
#COPY docker/files/odbcinst.ini /etc/odbcinst.ini

ARG DEPLOY_MODE=devel
ENV DEPLOY_MODE=${DEPLOY_MODE}
ENV LANG=en_CA.UTF-8
ENV IN_DOCKER=yes
WORKDIR /coursys

ARG UID=888
RUN useradd -s /bin/bash --uid ${UID} coursys
RUN mkdir /static && chown coursys /static
RUN ln -sf /csrpt_auth/krb5cc /tmp/krb5cc_${UID} # not all images have /csrpt_auth mounted, but ones that do will have the auth token in place

RUN mkdir -p /coursys
WORKDIR /coursys

COPY package.json /coursys/package.json
COPY package-lock.json /coursys/package-lock.json
RUN npm install

RUN pip install --upgrade pip
COPY requirements.txt /coursys/requirements.txt
RUN python3 -m pip install -r /coursys/requirements.txt

COPY --exclude=.git --exclude=node_modules --exclude=secrets --exclude=docker --exclude=*.yml --exclude=instructions \
  --exclude=submitted_files --exclude=whoosh_index --exclude=deploy --exclude=rhel \
  . /coursys
COPY courses/docker-localsettings-${DEPLOY_MODE}.py /coursys/courses/localsettings.py
COPY courses/docker-secrets-${DEPLOY_MODE}.py /coursys/courses/secrets.py

USER coursys

#RUN ./manage.py # check that file permissions are sane in the container: if this fails, check file permission in the source directory

CMD echo



# app image: config for actually handline web requests

FROM base AS app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl --fail http://localhost:8000/healthcheck || exit 1

ARG N_WORKERS=5
ENV N_WORKERS=${N_WORKERS}

CMD gunicorn --workers=${N_WORKERS} --worker-class=sync --max-requests=100 --max-requests-jitter=10 --bind 0.0.0.0:8000 courses.wsgi:application



# celery image: config for celery workers

FROM base AS celery

COPY docker/celery-worker.sh /celery-worker.sh
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl --fail http://localhost:9000/ || exit 1
ENV QUEUE=${QUEUE}
ENV CONCURRENCY=${CONCURRENCY}
CMD /celery-worker.sh



# celery beat image

FROM base AS beat
CMD celery -A courses beat --loglevel INFO



# management helper

FROM base AS manage
ENTRYPOINT ["python", "/coursys/manage.py"]
CMD ["shell"]