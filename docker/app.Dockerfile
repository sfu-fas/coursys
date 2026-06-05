FROM python:3.13

RUN apt-get update \
  && apt-get install -y locales-all npm libfreetype-dev default-mysql-client \
    unixodbc-dev krb5-user tdsodbc \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY docker/files/odbc.ini /etc/odbc.ini
COPY docker/files/krb5.conf /etc/krb5.conf
COPY docker/files/odbcinst.ini /etc/odbcinst.ini

ARG DEPLOY_MODE=devel
ENV DEPLOY_MODE=${DEPLOY_MODE}
ENV LANG=en_CA.UTF-8
ENV IN_DOCKER=yes
WORKDIR /coursys

ARG UID=888
RUN useradd -s /bin/bash --uid ${UID} coursys
RUN mkdir /static && chown coursys /static

RUN mkdir -p /coursys
WORKDIR /coursys

COPY package.json /coursys/package.json
COPY package-lock.json /coursys/package-lock.json
RUN npm install

RUN pip install --upgrade pip
COPY requirements.txt /coursys/requirements.txt
RUN python3 -m pip install -r /coursys/requirements.txt

HEALTHCHECK --interval=60s --timeout=5s --start-period=5s \
  CMD curl --fail http://localhost:8000/browse/?healthcheck || exit 1

COPY --exclude=node_modules . /coursys
COPY courses/docker-localsettings-${DEPLOY_MODE}.py /coursys/courses/localsettings.py
COPY courses/docker-secrets-${DEPLOY_MODE}.py /coursys/courses/secrets.py

ARG N_WORKERS=2
ENV N_WORKERS=${N_WORKERS}

USER coursys
RUN ./manage.py # check that file permissions are sane in the container: if this fails, check file permission in the source directory
CMD gunicorn --workers=${N_WORKERS} --worker-class=sync --max-requests=100 --max-requests-jitter=10 --bind 0.0.0.0:8000 courses.wsgi:application
