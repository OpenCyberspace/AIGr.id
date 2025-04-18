#!/bin/bash

#elastic search
kubectl create -f elastic-search.yaml
kubectl create -f elastic-search-svc.yaml

#fluentbit
kubectl create -f fluentbit/fluent-bit-role-binding.yaml
kubectl create -f fluentbit/fluent-bit-role.yaml 
kubectl create -f fluentbit/fluent-bit-service-account.yaml
kubectl create -f fluentbit/fluent-bit-configmap.yaml

kubectl create -f fluentbit/fluentbit.yaml 

#kibana
kubectl create -f kibana.yaml
