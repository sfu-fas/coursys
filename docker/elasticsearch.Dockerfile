FROM elasticsearch:7.17.28

HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --start-interval=5s CMD ["/elasticsearch-healthcheck.sh"]

COPY docker/files/elasticsearch.yml /usr/share/elasticsearch/config/elasticsearch.yml
COPY docker/files/elasticsearch-roles.yml /usr/share/elasticsearch/config/roles.yml
COPY --chmod=0755 docker/files/start-elasticsearch.sh /
COPY --chmod=0755 docker/files/elasticsearch-healthcheck.sh /

ENTRYPOINT ["/bin/tini", "--", "/start-elasticsearch.sh"]
