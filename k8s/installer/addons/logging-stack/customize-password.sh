#!/bin/bash

helm upgrade loki grafana/loki-stack \
  --namespace logging --create-namespace \
  --set grafana.enabled=true \
  --set grafana.adminUser=admin \
  --set grafana.adminPassword=admin