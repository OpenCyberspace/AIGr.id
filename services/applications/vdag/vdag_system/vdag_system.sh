#!/bin/bash

docker start runtime_db
docker run -d --rm --net=host --name=vdag-system vdag_system:v1
docker run -d --rm --net=host --name=vdag-db vdag_db:v1
docker run -d --rm --net=host --name=parser parser:v1
docker run -d --rm --net=host --name=blocks blocks_db:v1
docker run -d --rm --net=host --name=adhoc adhoc_inference:v1
