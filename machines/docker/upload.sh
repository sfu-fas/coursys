#!/bin/sh

sudo docker tag coursys-test ggbaker/coursys-test:latest
sudo docker login
sudo docker push ggbaker/coursys-test:latest