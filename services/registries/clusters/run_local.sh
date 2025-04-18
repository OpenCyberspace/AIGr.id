#!/bin/bash

sudo docker run -d  --net=host --name cluster_db \
    -e "MONGO_URL=mongodb://localhost:27017/clusters" \
    cluster_db:v1

sudo docker run -d --net=host --name cluster_gateway \
    -e "CLUSTER_SERVICE_URL=http://localhost:3000" \
    cluster_gateway:v1