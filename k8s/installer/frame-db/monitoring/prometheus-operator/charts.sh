#!/bin/bash

kubectl create secret -n framedb-monitoring generic framedb-datasource --from-file=datasource/datasource.yaml

kubectl create configmap -n framedb-monitoring framedb-dashboard --from-file=dashboard/framedb-chart.json

kubectl create configmap -n framedb-monitoring ambassador-dashboard --from-file=dashboard/ambassador.json

kubectl create configmap -n framedb-monitoring ceph-objects-dashboard --from-file=dashboard/ceph-cluster.json

kubectl create configmap -n framedb-monitoring tidb-dashboard --from-file=dashboard/tidb-cluster.json

kubectl create configmap -n framedb-monitoring cassandra-dashboard --from-file=dashboard/cassandra-cluster.json

kubectl create configmap -n framedb-monitoring mongodb-dashboard --from-file=dashboard/mongodb.json

kubectl create configmap -n framedb-monitoring k8s-cluster-capacity --from-file=k8s-charts/cluster_capacity.json

kubectl create configmap -n framedb-monitoring k8s-cluster-load --from-file=k8s-charts/cluster_load.json

kubectl create configmap -n framedb-monitoring k8s-pods --from-file=k8s-charts/pod_container.json


