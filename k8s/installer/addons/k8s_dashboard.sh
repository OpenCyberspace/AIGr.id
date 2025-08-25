#!/bin/bash

k5 create ns kubernetes-dashboard

# k create secret generic kubernetes-dashboard-csrf \
#   -n kubernetes-dashboard \
#  --from-literal=csrf="dashboard-csrf"

helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard \
  --create-namespace \
  --version 6.0.8 \
  --namespace kubernetes-dashboard \
  --set service.type=NodePort \
  --set service.nodePort=32319 \
  --kubeconfig=/home/cognitifai/configs/cluster-4-patch.yaml \
    --debug


k5 create serviceaccount dashboard-admin-sa -n kubernetes-dashboard

k5 create clusterrolebinding dashboard-admin-sa \
  --clusterrole=cluster-admin \
  --serviceaccount=kubernetes-dashboard:dashboard-admin-sa