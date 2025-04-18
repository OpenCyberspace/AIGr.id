#!/bin/bash

kubectl create -f ceph/crds.yaml -f ceph/common.yaml -f ceph/operator.yaml

