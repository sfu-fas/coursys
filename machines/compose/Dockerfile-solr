FROM solr:8

USER root
RUN mkdir /config \
  && cd /opt/solr/server/solr/configsets/_default/conf/ \
  && cp -r solrconfig.xml protwords.txt synonyms.txt stopwords.txt lang /config/ \
  && cp /opt/solr/example/files/conf/currency.xml /config/

COPY solr-schema.xml /config/schema.xml

USER solr
CMD solr-create -c coursys -d /config