import tomllib
config = tomllib.load(open('/run/secrets/app-config', 'rb'))

RABBITMQ_PASSWORD = config['rabbitmq']['password']
DB_CONNECTION = {
    'PASSWORD': config['database']['password'],
}
