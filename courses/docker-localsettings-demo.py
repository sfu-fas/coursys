DEPLOY_MODE = 'proddev'
DB_CONNECTION = {
    'HOST': 'mysql'
}
RABBITMQ_HOSTPORT = 'rabbitmq:5672'
MEMCACHED_HOST = 'memcached'
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'courselib.elasticsearch_backend.CustomElasticsearchSearchEngine',
        'URL': 'http://elasticsearch:9200/',
        'INDEX_NAME': 'haystack',
        'TIMEOUT': 60,
    },
}