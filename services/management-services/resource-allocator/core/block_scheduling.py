from .block_dry_runner import DryRunExecutor
from .cluster_db import ClusterClient
from .global_metrics import GlobalClusterMetricsClient

import os
import logging

logger = logging.getLogger("MainLogger")


def handle_dry_run(cluster_data, payload):
    try:
        dry_runner = DryRunExecutor(
            os.getenv("CLUSTER_DRY_RUN_MODE", "local"),
            payload['policy_rule_uri'],
            payload['settings'],
            payload['parameters'],
        )

        cluster_metrics = GlobalClusterMetricsClient()
        cluster_metrics = cluster_metrics.get_cluster(cluster_data['id'])

        full_input = {
            "block": payload['inputs'],
            "cluster": cluster_data,
            "cluster_metrics": cluster_metrics
        }

        return dry_runner.execute_dry_run(full_input)
    except Exception as e:
        logger.error(f"Error performing dry run: {e}")
        raise


def run_for_each_cluster(clusters, push_payload):
    try:

        all_responses = []

        for cluster in clusters:
            response = handle_dry_run(cluster, push_payload)
            all_responses.append(response)

        return all_responses

    except Exception as e:
        raise e
