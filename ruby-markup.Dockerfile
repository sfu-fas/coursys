FROM ruby:2.7

RUN bundle config --global frozen 1

COPY docker/Gemfile docker/Gemfile.lock ./
RUN bundle install
COPY docker/markdown2html-server.rb ./

CMD ["ruby", "markdown2html-server.rb"]