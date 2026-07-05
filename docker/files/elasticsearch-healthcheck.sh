#!/bin/bash

set -e

#echo "HEALTHCHECK" | tee /proc/1/fd/1
curl --max-time 10 "http://localhost:9200/_cluster/health" | tee /proc/1/fd/1  # dump the healthcheck results into the container log
curl --max-time 10 -f "http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=5s"
