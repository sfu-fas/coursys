## Proddev VM Setup

See `instructions/VM_PRODDEV.md` for setup information

## Production Server Setup

Get a VM.

```sh
sudo apt install git chef
git clone -b deployed-2022 https://github.com/sfu-fas/coursys.git
cd coursys
cp ./deploy/run-list-production.json ./deploy/run-list.json
# check ./deploy/solo.rb and ./deploy/run-list-production.json
make chef # will fail at nginx step because of missing cert...
cd /coursys
sudo cp ./deploy/run-list-production.json ./deploy/run-list.json
# re-check ./deploy/solo.rb and ./deploy/run-list.json from this installation
sudo rm -rf ~/coursys # probably: it's all in /coursys now
```

Double-check firewall rules: these recipes do not configure iptables, but only ports 80 and 443 should be open. Port 22 should be open to a limited IP range.
```sh
make chef
```

Check local settings:
```sh
sudo nano -w /coursys/courses/localsettings.py
sudo nano -w /coursys/courses/secrets.py
```

```shell
make start-all
```
