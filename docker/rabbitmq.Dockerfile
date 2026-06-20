FROM rabbitmq:4.2-alpine
# rabbitmq 4.3 compatibility fix pending a celery release: https://github.com/celery/kombu/issues/2237

HEALTHCHECK --interval=30s --timeout=30s --start-period=10s \
  CMD rabbitmq-diagnostics -q ping

COPY --chmod=0755 docker/files/start-rabbitmq.sh /

CMD ["/start-rabbitmq.sh"]