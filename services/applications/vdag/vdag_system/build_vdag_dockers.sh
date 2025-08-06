#!/bin/bash

docker build . -t vdag_system:v1

pushd ../../dbs/vdag
    docker build . -t vdag_db:v1
popd

pushd ../../parser
    docker build . -t parser:v1
popd
