DEPLOY_MODE = 'proddev'

BASE_ABS_URL = 'https://coursys-demo.selfip.net'
MORE_ALLOWED_HOSTS = ['coursys-demo.selfip.net']
MORE_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/coursys/db.sqlite',
    }
}