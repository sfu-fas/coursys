## Demo Server Setup

Create a VM.
```sh
sudo apt install chef
git clone https://github.com/sfu-fas/coursys.git
cd coursys/
git checkout some-branch
sudo chef-solo -c ./deploy/solo.rb -j ./deploy/run-list.json
cd
# rm -rf coursys # probably
cd /coursys
# probably edit /coursys/courses/localsettings.py
# get demo data dumped from production
./manage.py load_demo_data demodata.json 


```