#!/bin/bash

export CLUSTER_SERVICE_URL="http://164.52.207.172:30101"

export GLOBAL_SERVICES_MAP='{"global_block_metrics_redis_host": "redis://164.52.207.172:30200/0", "global_cluster_metrics_redis_host": "redis://164.52.207.172:30200/0", "global_vdag_metrics_redis_host": "redis://164.52.207.172:30200/0", "policy_db_url": "http://164.52.207.172:30102", "blocks_db_url": "http://164.52.207.172:30100", "cluster_db_url": "http://164.52.207.172:30101", "vdag_db_url": "http://164.52.207.172:30103", "vdag_controller_db_url": "http://164.52.207.172:30103"}'

export CLUSTER_CONTROLLER_GATEWAY_ACTIONS_MAP="{}"

export SEARCH_SERVER_API_URL="http://164.52.207.172:30150"

export CLUSTER_CONTROLLER_ROUTE=""

export CLUSTER_CONTROLLER_GATEWAY_POLICY_MAP="{}"

export POLICY_EXECUTOR_HOST_URL="http://164.52.207.172:30102"

export RESOURCE_ALLOCATOR_URL="ws://resource-allocator.utils.svc.cluster.local:8765"

export GLOBAL_BLOCK_METRICS_URL="http://global-block-metrics.metrics-system.svc.cluster.local:8889"

export POLICY_DB_URL="http://164.52.207.172:30102"

export BLOCKS_SERVICE_URL="http://blocks-db-svc.registries.svc.cluster.local:3001"

export GLOBAL_TASKS_DB_URL="http://164.52.207.172:30108"

export ALLOCATION_EXECUTION_MODE="offline"

export POLICY_SYSTEM_EXECUTOR_ID="executor-001"

export GLOBAL_CLUSTER_METRICS_URL="http://global-cluster-metrics.metrics-system.svc.cluster.local:8888"

export POLICY_EXECUTION_MODE="local"

export POLICY_RULE_REMOTE_URL="http://164.52.207.172:30102"

export METRICS_DAEMONSET_IMAGE_NAME="164.52.207.172:32633/cluster/daemon:latest"

export METRICS_WRITER_SERVICE_IMAGE_NAME="164.52.207.172:32633/cluster/metrics:latest"

export INFRA_CONTAINER_IMAGE_NAME="164.52.207.172:32633/cluster/infra:latest"

export BLOCK_TRANSACTIONS_CONTAINER_IMAGE_NAME="164.52.207.172:32633/cluster/block-tx:latest"

export PARAMETER_UPDATER_CONTAINER_IMAGE_NAME="164.52.207.172:32633/cluster/parameter-updater:latest"

export CLUSTER_MONITOR_CONTAINER_IMAGE_NAME="164.52.207.172:32633/cluster/monitor:latest"

export HEALTH_CHECKER_CONTAINER_IMAGE_NAME="164.52.207.172:32633/cluster/stability-checker:latest"


python3 main.py