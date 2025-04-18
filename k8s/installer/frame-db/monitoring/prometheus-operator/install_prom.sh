#!/bin/bash

helm install framedb-metrics-scraping bitnami/kube-prometheus \
    --values=values-prom.yaml \
    --create-namespace=true \
    --namespace=framedb-monitoring