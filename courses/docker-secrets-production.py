import tomllib
config = tomllib.load(open('/run/secrets/app-config', 'rb'))

RABBITMQ_PASSWORD = config['rabbitmq']['password']
DB_CONNECTION = {
    'PASSWORD': config['database']['password'],
}

SECRET_KEY = config['system']['django_secret']
EMPLID_API_SECRET = config['external']['emplid_api_secret']
#AMAINT_DB_PASSWORD = config['external']['amaint_password']
