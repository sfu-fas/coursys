FROM ubuntu:bionic
WORKDIR /code
ADD . /code/

RUN apt-get update \
  && apt-get install -y python3 python3-dev python3-pip \
    git mercurial ruby ruby-dev libmysqlclient-dev locales \
  && rm -rf /var/lib/apt/lists/* \
  && locale-gen en_CA.UTF-8
RUN pip3 install -r requirements.txt && gem install commonmarker github-markup

# duplicate 'pip3 install' when running, so Travis tests don't fail on every tiny library update
CMD pip3 install -r requirements.txt && LC_ALL=en_CA.UTF-8 python3 manage.py test
