DB_CONNECTION = {
    'NAME': '',
    'USER': '',
    'PASSWORD': '',
    'HOST': '',
    'PORT': '',
    'OPTIONS': {
        "init_command": "SET default_storage_engine=INNODB, character_set_client=utf8mb4, character_set_connection=utf8mb4, character_set_results=utf8mb4, collation_connection=utf8mb4_unicode_ci, collation_server=utf8mb4_unicode_ci;",
        'charset': 'utf8mb4'
    }
}

# 50-random-character secret key for crypto thingies. Use tools/secret_key_gen.py to create a good one if needed
SECRET_KEY = ''

# passwords for various connections:
AMAINT_DB_PASSWORD = ''
RABBITMQ_PASSWORD = 'the_rabbitmq_password' # must match the default for the rabbitmq container, as controlled by the .env file created by chef.
EMPLID_API_SECRET = ''
