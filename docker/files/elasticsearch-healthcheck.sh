#!/bin/bash

set -e

#echo "HEALTHCHECK" | tee /proc/1/fd/1
#curl --max-time 30 -i "http://localhost:9200/_cluster/health" | tee /proc/1/fd/1
curl --max-time 30 -f "http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=5s"
