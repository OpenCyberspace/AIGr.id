#!/bin/bash

docker start runtime_db

docker run --net=host -d --rm --name=tasks-writer aiosv1/status-writer:v1

docker run --net=host -d --rm --name=tasks-service aiosv1/status-service:v1