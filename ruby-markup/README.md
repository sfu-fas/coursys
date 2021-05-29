## About the ruby-markup code

This directory contains the code to create a Docker-based microservice that we use to
convert [Github-flavoured markdown](https://github.github.com/gfm/) to HTML.

The library to do this is Ruby-only, so we're doing some cross-language communication here
through RabbitMQ, which we have for Celery anyway. The Python side of this communication is
in `courselib/github_markdown.py`.


### Creating Gemfile.lock

Creating/updating the `Gemfile.lock` must be done outside of the container, with at least a
minimal Ruby development environment. Something like this:
```shell
sudo apt install ruby-bundler
cd ruby-markup
bundle install
git add Gemfile.lock
```
