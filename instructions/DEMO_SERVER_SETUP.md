# Demo Server Setup

## Server Configuration

Create a VM, with likely specs 2 cores, 8GB memory, 30GB disk.
```sh
wget https://packages.chef.io/files/stable/chef-workstation/21.10.640/ubuntu/20.04/chef-workstation_21.10.640-1_amd64.deb
sudo dpkg -i chef-workstation*.deb
git clone https://github.com/sfu-fas/coursys.git
cd coursys/
git checkout master  # or some other branch if you like
sudo cp ./deploy/run-list-demo.json ./deploy/run-list.json # check run-list.json and solo.rb to make sure they're correct
sudo chef-solo -c ./deploy/solo.rb -j ./deploy/run-list.json
```

You'll probably want to log out/in to get your permissions updated (with the docker group). Then continue with the "real" code location...
```shell
rm -rf ~/coursys # probably
cd /coursys
sudo cp ./deploy/run-list-demo.json ./deploy/run-list.json # again check run-list.json and solo.rb
```

The `localsettings.py` will probably be something like:
```python
DEPLOY_MODE = 'proddev'

BASE_ABS_URL = 'http://coursys-demo.selfip.net'
MORE_ALLOWED_HOSTS = ['coursys-demo.selfip.net']
MORE_SERVE_HOSTS = ['coursys-demo.selfip.net']

import os
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
```


## Demo Data

For the demo system, we use a mix of real-but-public data, and enough fake data to work with.

On the *production* server, capture the basic public info we want to have:
```shell
./manage.py dump_demo_data > /tmp/demodata.json
```

Copy `demodata.json` to the demo server and **on the demo server**:
```shell
cd /coursys
./manage.py migrate
./manage.py load_demo_data ~/demodata.json
./manage.py rebuild_index
make start-all
```


## Purging Data

```shell
make proddev-stop
make proddev-rm-all
sudo rm -rf /data/mysql/*
make proddev-start
./manage.py migrate
```


## SSL/TLS Setup: legacy no longer used

Since the SFU load balancer terminates HTTPS for us, our configuration system doesn't typically know about SSL. We used to, and the demo server thus also had an https:// URL. This is now really painful to set up, so we have been using unencrypted http:// for the demo server. These instructions are therefore vestigial, but seem worth retaining here, just in case.

At some point, Chef will fail because the certificate is missing. Either copy `/etc/letsencrypt` from an old server, or comment-out all SSL server sections from the `/etc/nginx` config and:
```shell
sudo snap install --classic certbot
sudo certbot --nginx
```

And patch up the nginx+ssh config:
```sh
sudo openssl dhparam -out /etc/nginx/dhparams.pem 2048
sudo grep -v "^\s*ssl_" /etc/nginx/nginx.conf > /tmp/nginx.conf
sudo cp /tmp/nginx.conf /etc/nginx/nginx.conf
sudo cp /coursys/deploy/demo-deploy/nginx-default.conf /etc/nginx/sites-available/default
sudo cp /coursys/deploy/demo-deploy/nginx-site.conf /etc/nginx/sites-available/coursys-demo.selfip.net.conf
sudo systemctl restart nginx gunicorn celery celerybeat
```
