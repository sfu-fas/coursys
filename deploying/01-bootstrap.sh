#!/bin/false

# These commands (at least) would need to be done manually, as needed,
# before retrieving the rest of the repository.

# Needed only in the data centre:
echo "export HTTP_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080" >> ~/.bashrc
echo "export HTTPS_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"  >> ~/.bashrc
echo "export NO_PROXY=localhost,.sfu.ca,*.sfu.ca" >> ~/.bashrc
. ~/.bashrc

echo 'Defaults env_keep += "HTTP_PROXY HTTPS_PROXY NO_PROXY"' | sudo tee /etc/sudoers.d/coursys

# In general:
sudo dnf install -y git
git clone https://github.com/sfu-fas/coursys.git /tmp/coursys -b master
sudo mv /tmp/coursys /coursys
cd /coursys/deploy

# have a look at config.sh; edit as needed
