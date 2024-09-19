# Demo Server Setup

## Server Configuration

Create a VM.
```sh
wget https://packages.chef.io/files/stable/chef-workstation/21.10.640/ubuntu/20.04/chef-workstation_21.10.640-1_amd64.deb
sudo dpkg -i chef-workstation*.deb
git clone https://github.com/sfu-fas/coursys.git
cd coursys/
git checkout master
sudo cp ./deploy/run-list-demo.json ./deploy/run-list.json # check run-list.json to make sure it's correct
sudo chef-solo -c ./deploy/solo.rb -j ./deploy/run-list.json # will fail at nginx step because of missing cert...
```

That last step will fail because the certificate is missing. Either copy `/etc/letsencrypt` from an old server, or comment-out all SSL server sections from the `/etc/nginx` config and:
```shell
sudo snap install --classic certbot
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

from django.utils.safestring import mark_safe
SERVER_MESSAGE_INDEX = mark_safe('''<p class="infomessage"><i class="fas fa-info-circle"></i>
    Welcome to the CourSys demo server. You can experiment here consequence-free. You can fake-authenticate as other
    users as needed to explore the system. No emails will be sent by anything here, but they will be
    <a href="http://localhost:8025">visible publicly here</a> if you'd like to inspect them.</p>
''')
SERVER_MESSAGE = mark_safe('''<p class="warningmessage"><i class="fas fa-exclamation-triangle"></i>
    This demo server is publicly available and unauthenticated: no confidential or personally-identifying information
    should be entered anywhere here.
</p>''')
```

This configures the system to send email to the included [smtp4dev](https://github.com/rnwood/smtp4dev) destination. All email can be viewed at: http://coursys-demo.selfip.net:8025/

Then get things started:
```shell
sudo mkdir /opt/submitted_files && sudo chown cloud-user /opt/submitted_files
sudo service docker restart  # for its networking setup
make proddev-start
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
make proddev-stop
make proddev-rm-all
sudo rm -rf /data/mysql/*
make proddev-start
./manage.py migrate
make rebuild-hardcore
./manage.py load_demo_data /tmp/demo_data.json
./manage.py rebuild_index
```

And patch up the nginx+ssh config:
```sh
sudo openssl dhparam -out /etc/nginx/dhparams.pem 2048
sudo grep -v "^\s*ssl_" /etc/nginx/nginx.conf > /tmp/nginx.conf
sudo cp /tmp/nginx.conf /etc/nginx/nginx.conf
sudo cp /coursys/deploy/demo-deploy/nginx-default.conf /etc/nginx/sites-available/default
sudo cp /coursys/deploy/demo-deploy/nginx-site.conf coursys-demo.selfip.net.conf
sudo systemctl restart nginx gunicorn celery celerybeat
```
