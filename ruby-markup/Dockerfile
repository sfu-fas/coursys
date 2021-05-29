FROM ruby:3.0

RUN bundle config --global frozen 1

COPY Gemfile Gemfile.lock ./
RUN bundle install

COPY wait.sh /wait
RUN chmod +x /wait

COPY markdown2html-server.rb ./

CMD /wait rabbitmq 5672 \
  && ruby markdown2html-server.rb