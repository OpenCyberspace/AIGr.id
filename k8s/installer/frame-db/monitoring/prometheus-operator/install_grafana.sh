#!/bin/bash

helm install framedb-metrics-dashboard bitnami/grafana \
    --values=values-grafana.yaml \
    --create-namespace=true \
    --namespace=framedb-monitoring