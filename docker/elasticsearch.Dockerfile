FROM elasticsearch:7.17.28

HEALTHCHECK --interval=60s --timeout=30s --start-period=15s \
  CMD curl -s http://localhost:9200 >/dev/null || exit 1

COPY --chmod=0755 docker/files/start-elasticsearch.sh /

ENTRYPOINT ["/bin/tini", "--", "/start-elasticsearch.sh"]
