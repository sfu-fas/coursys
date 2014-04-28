#!/bin/sh
sudo su - www-data -c "cd /home/coursys/courses; LD_LIBRARY_PATH=/home/coursys/sqllib/lib64 /home/coursys/courses/manage.py check_things"
