## Proddev VM Setup

Start with a `vagrant up`. In the VM,
```sh
cd /coursys
docker-compose -f docker-compose.yml -f docker-compose-proddev.yml up -d
./manage.py migrate
./manage.py loaddata fixtures/*.json
./manage.py update_index
make proddev-start-all
```

## Demo Server Setup

Create a VM.
```sh
sudo apt install chef
git clone https://github.com/sfu-fas/coursys.git
cd coursys/
git checkout some-branch
sudo chef-solo -c ./deploy/solo.rb -j ./deploy/run-list.json
sudo certbot --nginx certonly
cd
# rm -rf coursys # probably
cd /coursys
# probably edit /coursys/courses/localsettings.py
# get demo data dumped from production
./manage.py load_demo_data demodata.json 
```