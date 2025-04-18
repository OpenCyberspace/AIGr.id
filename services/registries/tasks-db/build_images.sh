#!/bin/bash

pushd service
    docker build . -t aiosv1/status-service:v1
popd

pushd writer
    docker build . -t aiosv1/status-writer:v1
popd