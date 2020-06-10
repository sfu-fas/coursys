FROM python:3.8

WORKDIR /coursys
RUN chown www-data:www-data /coursys

# adapted from https://github.com/gettyimages/docker-spark/blob/master/Dockerfile
RUN apt-get update \
 && apt-get install -y locales \
 && dpkg-reconfigure -f noninteractive locales \
 && locale-gen en_CA.UTF-8 \
 && /usr/sbin/update-locale LANG=C.UTF-8 \
 && echo "en_CA.UTF-8 UTF-8" >> /etc/locale.gen \
 && locale-gen \
 && apt-get install -y default-mysql-client \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt && pip install ipython

#RUN mkdir /var/log/celery/ /var/run/celery/ && chown www-data.www-data /var/log/celery/ /var/run/celery/

COPY docker/wait.sh /wait
RUN chmod +x /wait

RUN mkdir /static
RUN chown www-data:www-data /static

COPY . /coursys

#USER www-data
ENV PYTHONUNBUFFERED 1
# /wait db 3306 && 
CMD /wait elasticsearch 9200 && /wait memcached 11211 && /wait rabbitmq 5672 \
  && /usr/local/bin/gunicorn --workers=2 --worker-class=sync --max-requests=1000 --bind 0:8000 courses.wsgi:application

