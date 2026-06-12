FROM rabbitmq:3-alpine

HEALTHCHECK --interval=30s --timeout=30s --start-period=10s \
  CMD rabbitmq-diagnostics -q ping

COPY docker/files/start-rabbitmq.sh /

CMD ["/start-rabbitmq.sh"]