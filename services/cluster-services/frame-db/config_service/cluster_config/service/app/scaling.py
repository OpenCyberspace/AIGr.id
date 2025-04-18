from kubernetes import config, client
from fastapi import APIRouter, Request
import time
from .db.db_api import DBApi
from .k8s_api import K8sApi
from .utils import validate_json_fields, with_logging, send_error_message, send_success_message

import logging
logging = logging.getLogger("MainLogger")


def log_request(request: Request, dictPayload: dict = None):

    url = request.url.path
    logging.info(
        "{} got hit".format(url),
        extra={
            "client_host": request.client.host,
            "client_port": request.client.port,
            "payload": str(dictPayload) if dictPayload else None,
            "endpoint": url
        }
    )


class FramedbScaler:

    @staticmethod
    def getChangedPods(old_pod_list: list, new_pod_list: list):

        new_pod_set = set([pod.metadata.name for pod in new_pod_list])
        old_pod_set = set(old_pod_list)

        print(old_pod_set - new_pod_set)

        if len(old_pod_list) > len(new_pod_list):
            return True, (old_pod_set - new_pod_set)
        else:
            return False, (new_pod_set - old_pod_set)

    @staticmethod
    def UpdatePodsListInDB(clusterSpec, pod_list, changed_pods, scale_down=False):

        if scale_down:
            # get a list of framedb_ids that have been removed
            podsToDelete = list(changed_pods)
            podsToRetain = [
                podId.metadata.name for podId in pod_list if podId.metadata.name not in changed_pods]

            print('Retaining ', podsToRetain)
            print('Deleting ', podsToDelete)

            # call delete on mongodb
            ret, message = DBApi.RemoveFrameDBs(
                clusterSpec.cluster_name,
                podsToDelete,
                podsToRetain
            )
            return ret, message

        # scale-up
        new_pods_to_add = [
            podId.metadata.name for podId in pod_list if podId.metadata.name in changed_pods]
        ret, result = DBApi.AddFramedDBs(
            clusterSpec.cluster_name, pod_list, new_pods_to_add)
        return ret, result

    @staticmethod
    def PodsGotIp(pod_data):

        for pod in pod_data:
            if (not pod.status.pod_ip) or (not pod.status.host_ip):
                return False

        return True

    @staticmethod
    def ScaleReplicas(cluster_id, n_replicas):
        # loads config from KUBECONFIG env variable
        if n_replicas < 0:
            return False, "n_replicas must be > 0"

        k8Client = K8sApi.GetK8sApiClient()

        # scale replicas using StatefulSpec
        ret, clusterSpec = DBApi.GetClusterSpec(cluster_id)
        if not ret:
            return False, "Cluster {} does not exist".format(cluster_id)

        if len(clusterSpec.clusterPods) == n_replicas:
            return True, "Replicas {} already exist".format(n_replicas)

        if n_replicas == 0:
            return False, "Scale to Zero is not allowed, delete the deployment instead"

        # get cluster sts name
        sts_name = clusterSpec.cluster_name
        sts_name = "{}-redis-node".format(sts_name)
        namespace = clusterSpec.namespace

        old_replicas = len(clusterSpec.clusterPods)

        try:

            scaledResponse = K8sApi.ScaleStatefulSet(
                k8Client, sts_name, namespace, n_replicas
            )

            # check if scaling is successful :
            # number of pods  == n_replicas
            if scaledResponse.spec.replicas != n_replicas:
                return False, "Scaling framedb {} failed".format(sts_name)

            # get pods:
            coreApi = K8sApi.GetK8sCoreApi()

            # time.sleep(3)

            framedbPods = []
            while True:
                time.sleep(3)
                framedbPods = K8sApi.GetPodsByStatefulSet(
                    coreApi, clusterSpec.cluster_name, namespace)
                if (len(framedbPods) != n_replicas) or not FramedbScaler.PodsGotIp(framedbPods):
                    logging.warning(
                        "One of the pods did not get IPs. So looping back")
                    continue
                else:
                    break

            # get changed pods
            scaleDown, changed_pods = FramedbScaler.getChangedPods(
                clusterSpec.clusterPods, framedbPods)
            ret, message = FramedbScaler.UpdatePodsListInDB(
                clusterSpec, framedbPods, changed_pods, scaleDown)

            if not ret:
                print(
                    'failed to update cluster in DB, reverting back the previous state....')
                logging.error(
                    'failed to update cluster in DB, reverting back the previous state....')

                scaledResponse = K8sApi.ScaleStatefulSet(
                    k8Client, sts_name, namespace, old_replicas
                )

                if scaledResponse.spec.replicas != old_replicas:
                    return False, "Failed to revert back previous state"

                return False, "Failed to update pod config in DB, but reverted back to previous cluster state"

            return True, "Cluster properly scaled up"

        except Exception as e:
            logging.error(e)
            return False, str(e)


replicasRouter = APIRouter()


@with_logging("/replication/createReplication")
@replicasRouter.post("/createReplication")
async def replicateSlaves(body: dict, request: Request):

    log_request(request, body)

    ret, fields = validate_json_fields(body, ['clusterId', 'replicas'])
    if not ret:
        return send_error_message("Missing field " + fields)

    ret, result = FramedbScaler.ScaleReplicas(
        body['clusterId'], body['replicas'])
    if not ret:
        return send_error_message(result)

    return send_success_message(result)
