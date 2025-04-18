#!/bin/bash

helm install framedb-kafka bitnami/kafka --values=production.yaml --namespace=framedb-storage --set zookeeper.persistence.enabled=false --set rbac.create=true