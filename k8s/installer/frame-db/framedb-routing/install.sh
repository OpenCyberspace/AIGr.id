#!/bin/bash

helm repo add bitnami https://charts.bitnami.com/bitnami

helm repo update

echo "Installing routing mongodb - framedb-routing"

helm install \
   framedb-routing-db \
   bitnami/mongodb \
   --namespace=framedb-routing --values=./mongodb/values.yaml --create-namespace=true

echo "Installing redis router pub-sub service"
helm install \
    framedb-routing-pub-sub \
    bitnami/redis \
    --namespace=framedb-routing --values=./redis/values-production.yaml --create-namespace=true

