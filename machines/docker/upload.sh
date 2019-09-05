#!/bin/sh

sudo docker tag ggbaker/coursys-test ggbaker/coursys-test-py3:latest
sudo docker login
sudo docker push ggbaker/coursys-test-py3:latest