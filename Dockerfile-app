# start containerized development deployment with:
# cd machines/compose && docker-compose up

FROM python:3.6
WORKDIR /code

# adapted from https://github.com/gettyimages/docker-spark/blob/master/Dockerfile
RUN apt-get update \
 && apt-get install -y locales \
 && dpkg-reconfigure -f noninteractive locales \
 && locale-gen en_CA.UTF-8 \
 && /usr/sbin/update-locale LANG=C.UTF-8 \
 && echo "en_CA.UTF-8 UTF-8" >> /etc/locale.gen \
 && locale-gen \
 && apt-get install -y mysql-client ruby ruby-dev \
 && gem install commonmarker github-markup \
 && curl -sL https://deb.nodesource.com/setup_12.x | bash - \
 && apt-get install -y nodejs \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt && pip install ipython

RUN mkdir /var/log/celery/ /var/run/celery/ && chown www-data.www-data /var/log/celery/ /var/run/celery/

COPY machines/compose/wait.sh /wait
RUN chmod +x /wait

RUN mkdir /static
RUN chown www-data:www-data /static

COPY package.json /npm/
COPY package-lock.json /npm/
RUN cd /npm && npm install

USER www-data
ENV PYTHONUNBUFFERED 1
# TODO: the setup commands here should be somewhere else, possibly a dedicated "setup" container
CMD /wait db 3306 && /wait solr 8983 \
  && python3 ./manage.py migrate \
  && python3 ./manage.py loaddata fixtures/*.json \
  && python3 ./manage.py collectstatic --noinput \
  && python3 ./manage.py update_index \
  && /usr/local/bin/gunicorn --workers=5 --worker-class=sync --max-requests=1000 --bind 0:8000 courses.wsgi:application

