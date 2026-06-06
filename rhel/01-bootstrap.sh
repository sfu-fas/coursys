#!/bin/false

# These commands (at least) would need to be done manually, as needed,
# before retrieving the rest of the repository.

echo "HTTP_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080" >> ~/.bashrc
echo "HTTPS_PROXY=http://bby-vcontrol-proxy.its.sfu.ca:8080"  >> ~/.bashrc
echo "NO_PROXY=localhost,.sfu.ca,*.sfu.ca" >> ~/.bashrc
. ~/.bashrc

dnf install -y git
git clone https://github.com/sfu-fas/coursys.git
cd coursys
git checkout -b master