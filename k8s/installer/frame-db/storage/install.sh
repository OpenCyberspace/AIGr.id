#!/bin/bash

DIR_CEPH="ceph"
DIR_TIDB="TiCluster"

MODE=$1

install_rook () {
    mode=$1

    if [[ "$mode" == "fs" ]]; then 
        pushd ${DIR_CEPH}
        kubectl create -f common.yaml
        kubectl create -f operator.yaml
        kubectl create -f cluster.yaml
        popd
    fi 

    if [[ "$mode" == "pvc" ]]; then 
        pushd ${DIR_CEPH} 
        kubectl create -f common.yaml
        kubectl create -f operator.yaml 
        kubectl create -f cluster-on-pvc.yaml
        popd
    fi 

    echo "deployed Rook, Ceph and Ceph dashboard...."
}

install_tidb () {

    add_helm_repo () {
        helm repo add pingcap https://charts.pingcap.org/
        helm repo update

        echo "added TiDB helm repo"
    }

    #functions to set-up TiDB cluster
    intall_provisioner () {
        #installs a local stoage provisioner
        pushd TiCluster
        kubectl create -f local-volume-provisioner.yaml
        popd

        echo "installed storage provisioner"

    }

    install_crd () {
        pushd TiCluster
        kubectl create -f crd.yaml
        popd

        echo "installed Ti-CRD"
    }

    install_operator () {
        pushd TiCluster
        helm install --namespace=framedb-storage-operator --values=values.yaml tidb-operator-framedb pingcap/tidb-operator
        popd

        echo "installed TiDB operator"
    }

    install_cluster () {
        pushd TiCluster
        kubectl create -n framedb-storage-cluster -f tidb-cluster.yaml
        popd

        echo "installed TiDB Cluster"
    }

    install_monitoring () {
        pushd TiCluster
        kubectl create -n framedb-storage-cluster -f tidb-monitor.yaml
        popd
    }

    kubectl create namespace framedb-storage-operator
    kubectl create namespace framedb-storage-cluster
    add_helm_repo
    intall_provisioner
    install_crd
    install_operator
    install_cluster
    install_monitoring
}

remove_tidb () {
    pushd TiCluster
    kubectl delete -f local-volume-provisioner.yaml -n kube-system
    kubectl delete -f crd.yaml
    kubectl delete -f tidb-cluster.yaml -n framedb-storage-cluster
    kubectl delete -f tidb-monitor.yaml -n framedb-storage-cluster
    helm uninstall tidb-operator-framedb --namespace=framedb-storage-operator
    kubectl delete ns framedb-storage-cluster
    kubectl delete ns framedb-storage-operator
    popd
}

if [[ "$MODE" == "install" ]]; then
    install_tidb
fi

if [[ "$MODE" ==  "delete" ]]; then 
    remove_tidb
fi

if [[ "$MODE" == "ceph" ]]; then 
    install_rook fs
fi

