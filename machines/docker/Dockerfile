FROM ubuntu:yakkety
WORKDIR /code
ADD . /code/

RUN apt-get update \
  && apt-get install -y python python-dev python-pip \
    git mercurial \
  && rm -rf /var/lib/apt/lists/*
RUN locale-gen en_CA.UTF-8
RUN pip install -r build_deps/working_deps.txt

CMD ./manage.py test