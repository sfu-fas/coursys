#!/bin/sh
set -e

. $HOME/sqllib/db2profile
LANG="en_CA.UTF-8" # DB2 doesn't return UTF-8 strings otherwise
export LANG

cd /home/ggbaker/courses/
time python coredata/importer.py < /home/ggbaker/dbpass
