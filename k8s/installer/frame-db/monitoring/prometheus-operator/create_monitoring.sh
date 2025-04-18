#!/bin/bash

helm repo update

#install promethus-operator with 
helm install framedb-metrics-scraping bitnami/kube-prometheus \
    --values=values-prom.yaml \
    --create-namespace=true \
    --namespace=framedb-monitoring


#install datasource secret for framedb
#!/bin/bash

kubectl create secret -n framedb-monitoring generic framedb-datasource --from-file=datasource/datasource.yaml

kubectl create configmap -n framedb-monitoring framedb-dashboard --from-file=dashboard/framedb-chart.json

kubectl create configmap -n framedb-monitoring ambassador-dashboard --from-file=dashboard/ambassador.json

kubectl create configmap -n framedb-monitoring cassandra-dashboard --from-file=dashboard/cassandra-cluster.json

kubectl create configmap -n framedb-monitoring mongodb-dashboard --from-file=dashboard/mongodb.json

kubectl create configmap -n framedb-monitoring k8s-cluster-capacity --from-file=k8s-charts/cluster_capacity.json

kubectl create configmap -n framedb-monitoring k8s-cluster-load --from-file=k8s-charts/cluster_load.json

kubectl create configmap -n framedb-monitoring k8s-pods --from-file=k8s-charts/pod_container.json


#install grafana
helm install framedb-metrics-dashboard bitnami/grafana \
    --values=values-grafana.yaml \
    --create-namespace=true \
    --namespace=framedb-monitoring
