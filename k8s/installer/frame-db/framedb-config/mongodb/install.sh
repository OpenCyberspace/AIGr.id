#!/bin/bash

helm repo add bitnami https://charts.bitnami.com/bitnami

helm repo update

helm install \
   framedb-config-db \
   bitnami/mongodb \
   --namespace=framedb-config --values=./values.yaml --create-namespace=true