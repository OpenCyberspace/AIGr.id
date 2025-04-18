import os
import logging
import os

from .aiosv1 import ClusterController, get_envs
from .k8s import K8sConnection
from .block import BlocksDB
from .cluster import ClusterClient


class InitContainerExecutor:

    def __init__(self, container_class):
        try:
            self.envs = get_envs()
            ret, resp = BlocksDB().get_block_by_id(self.envs['block_id'])
            if not ret:
                raise Exception(str(resp))
            self.block_data = resp

            ret, resp = ClusterClient().read_cluster(self.envs['cluster_id'])
            if not ret:
                raise Exception(str(resp))

            self.cluster_data = resp

            # create K8s connection:
            self.k8s = K8sConnection()
            self.controller = ClusterController()

            self.executor_class = container_class(
                self.envs, self.block_data, self.cluster_data, self.k8s, self.envs['operating_mode']
            )

        except Exception as e:
            raise e

    def execute(self):
        try:

            ret, resp = self.executor_class.begin()
            if not ret:
                raise Exception(str(resp))

            # send begin successful status:
            self.controller.send_status_update({
                "status": "success",
                "stage": "begin",
                "message": resp,
                "mode": self.envs['operating_mode'],
                "status_data": resp
            })

            logging.info(f"begin state complete, resp={resp}")

            # execute main step
            ret, resp = self.executor_class.main()
            if not ret:
                raise Exception(str(resp))

            # send begin successful status:
            self.controller.send_status_update({
                "status": "success",
                "stage": "main",
                "message": resp,
                "mode": self.envs['operating_mode'],
                "status_data": resp
            })

            logging.info(f"main state complete, resp={resp}")

            # execute main step
            ret, resp = self.executor_class.finish()
            if not ret:
                raise Exception(str(resp))

            # send begin successful status:
            self.controller.send_status_update({
                "status": "success",
                "stage": "finish",
                "message": resp,
                "mode": self.envs['operating_mode'],
                "status_data": resp
            })

            logging.info(f"finish state complete, resp={resp}")

        except Exception as e:
            logging.error(f"failed to execute init container: {e}")
            self.controller.send_status_update({
                "status": "failed",
                "status_data": str(e)
            })
            raise e


def execute_init_container(main_class):
    try:

        executor = InitContainerExecutor(main_class)
        executor.execute()

    except Exception as e:
        os._exit(0)
