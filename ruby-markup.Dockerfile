FROM ruby:2.7

RUN bundle config --global frozen 1

COPY docker/Gemfile docker/Gemfile.lock ./
RUN bundle install
COPY docker/markdown2html-server.rb ./

COPY docker/wait.sh /wait
RUN chmod +x /wait

CMD /wait rabbitmq 5672 \
  && ruby markdown2html-server.rb