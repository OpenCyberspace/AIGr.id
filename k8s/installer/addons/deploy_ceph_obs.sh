#!/bin/bash

kubectl create -f ceph/cluster.yaml
kubectl create -f ceph/obs.yaml

