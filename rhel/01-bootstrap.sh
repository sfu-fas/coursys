#!/bin/false

# These commands (at least) would need to be done manually, as needed,
# before retrieving the rest of the repository.

echo "export HTTP_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080" >> ~/.bashrc
echo "export HTTPS_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"  >> ~/.bashrc
echo "export NO_PROXY=localhost,.sfu.ca,*.sfu.ca" >> ~/.bashrc
. ~/.bashrc

echo "export HTTP_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080" >> /root/.bashrc
echo "export HTTPS_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"  >> /root/.bashrc
echo "export NO_PROXY=localhost,.sfu.ca,*.sfu.ca" >> /root/.bashrc
#git config --global http.proxy http://bby-vcontrol-proxy.its.sfu.ca:8080

# visudo and add:
# Default    env_keep += "HTTP_PROXY HTTPS_PROXY NO_PROXY"

sudo dnf install -y git
git clone https://github.com/sfu-fas/coursys.git /tmp/coursys -b master
sudo mv /tmp/coursys /coursys
sudo chown -R root /coursys
cd /coursys/rhel

# have a look at config.sh; edit as needed
