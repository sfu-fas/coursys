# Demo Server Setup

## Server Configuration

Create a VM.
```sh
sudo apt install chef
git clone https://github.com/sfu-fas/coursys.git
cd coursys/
git checkout master
sudo cp ./deploy/run-list-demo.json ./deploy/run-list.json # check run-list.json to make sure it's correct
make chef # will fail at nginx step because of missing cert...
```

That last step will fail because the certificate is missing. Either copy `/etc/letsencrypt` from an old server, or comment-out all SSL server sections from the `/etc/nginx` config and:
```shell
sudo certbot --nginx
make chef
cd
rm -rf ~/coursys # probably
cd /coursys
sudo cp ./deploy/run-list-demo.json ./deploy/run-list.json # again check run-list.json
```

The `localsettings.py` will probably be something like:
```python
DEPLOY_MODE = 'proddev'

BASE_ABS_URL = 'https://coursys-demo.selfip.net'
MORE_ALLOWED_HOSTS = ['coursys-demo.selfip.net']
MORE_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/coursys/db.sqlite',
    }
}

import os
MOSS_DISTRIBUTION_PATH = os.path.join(os.environ['HOME'], 'moss')
DB_BACKUP_DIR = os.path.join(os.environ['COURSYS_DATA_ROOT'], 'db_backup')
SUBMISSION_PATH = os.path.join(os.environ['COURSYS_DATA_ROOT'], 'submitted_files')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 2525
EMAIL_USE_SSL = False
```

This configures the system to send email to the included [smtp4dev](https://github.com/rnwood/smtp4dev) destination. All email can be viewed at: http://coursys-demo.selfip.net:8025/

Then get things started:
```shell
make proddev-start-all
make start-all
```


## Demo Data

For the demo system, we use a mix of real-but-public data, and enough fake data to work with.

On the production server, capture the basic public info we want to have:
```shell
./manage.py dump_demo_data > /tmp/demodata.json
```

Copy `demodata.json` to the demo server and **on the demo server**:
```shell
cd /coursys
rm db.sqlite
./manage.py migrate
./manage.py load_demo_data /tmp/demo.json
```

