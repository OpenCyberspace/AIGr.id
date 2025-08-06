#!/bin/bash

helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm install loki grafana/loki-stack \
  --namespace logging --create-namespace \
  --set loki.persistence.enabled=false \
  --set promtail.enabled=true \
  --set grafana.enabled=true \
  --set grafana.adminUser=admin \
  --set grafana.adminPassword=admin \
  --set grafana.service.type=NodePort \
  --set grafana.service.nodePort=32199 \
  --kubeconfig=/home/cognitifai/configs/cluster-1-patch.yaml
