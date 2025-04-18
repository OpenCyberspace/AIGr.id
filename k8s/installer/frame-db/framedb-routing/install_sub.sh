#!/bin/bash

echo "Installing redis router pub-sub service"
helm install \
    framedb-routing-pub-sub \
    bitnami/redis \
    --namespace=framedb-routing --values=./redis/values-production.yaml --create-namespace=true  \
    --version=v11.2.3
