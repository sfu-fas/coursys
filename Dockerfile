# start containerizedd development deployment with:
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
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt && pip install ipython

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.5.0/wait /wait
RUN chmod +x /wait

#CMD /wait && python3 ./manage.py migrate && python3 ./manage.py loaddata fixtures/*.json && python3 ./manage.py runserver 0:8000
CMD /wait \
  && python3 ./manage.py migrate \
  && python3 ./manage.py loaddata fixtures/*.json \
  && /usr/local/bin/gunicorn --workers=5 --worker-class=sync --max-requests=1000 --bind 0:8000 courses.wsgi:application
