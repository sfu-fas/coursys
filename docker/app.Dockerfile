FROM python:3.13

RUN apt-get update \
  && apt-get install -y locales-all npm libfreetype-dev default-mysql-client \
  && apt-get install -y unixodbc-dev krb5-user tdsodbc \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ARG DEPLOY_MODE=devel
ENV DEPLOY_MODE=${DEPLOY_MODE}
ENV LANG=en_CA.UTF-8
ENV IN_DOCKER=yes
WORKDIR /coursys

RUN useradd -s /bin/bash coursys
RUN mkdir /static && chown coursys /static

RUN pip install --upgrade pip
COPY requirements.txt /requirements.txt
RUN python3 -m pip install -r /requirements.txt

COPY . /coursys
COPY courses/docker-localsettings-${DEPLOY_MODE}.py /coursys/courses/localsettings.py
COPY courses/docker-secrets-${DEPLOY_MODE}.py /coursys/courses/secrets.py

ARG N_WORKERS=2
ENV N_WORKERS=${N_WORKERS}

USER coursys
CMD gunicorn --workers=${N_WORKERS} --worker-class=sync --max-requests=100 --max-requests-jitter=10 --bind 0.0.0.0:8000 courses.wsgi:application