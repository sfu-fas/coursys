FROM ubuntu:yakkety
WORKDIR /code
ADD . /code/

RUN apt-get update \
  && apt-get install -y python python-dev python-pip \
    git mercurial \
  && rm -rf /var/lib/apt/lists/*
RUN locale-gen en_CA.UTF-8
RUN pip install -r build_deps/working_deps.txt

# duplication 'pip install' when running, so Travis tests don't fail on every tiny library update
CMD pip install -r build_deps/working_deps.txt && ./manage.py test