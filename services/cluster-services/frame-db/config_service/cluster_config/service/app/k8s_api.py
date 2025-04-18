from kubernetes import client, config


class K8sApi :

    @staticmethod
    def GetK8sApiClient() :
        config.load_kube_config()
        return client.AppsV1Api()
    
    @staticmethod
    def ScaleStatefulSet(apiClient : client.AppsV1Api, clusterName : str, namespace : str, replication : int) :

        print(apiClient, clusterName, namespace, replication)

        response = apiClient.patch_namespaced_stateful_set(
            name = clusterName,
            namespace = namespace,
            body = {"spec" : {"replicas" : replication}}
        )

        return response
    
    @staticmethod
    def GetK8sCoreApi() :
        config.load_kube_config()
        return client.CoreV1Api()
    
    @staticmethod
    def GetPodsByStatefulSet(apiClient : client.CoreV1Api, clusterName : str, namespace : str) :

        response = apiClient.list_namespaced_pod(
            namespace = namespace,
            label_selector = 'release={}'.format(clusterName)
        )

        return response.items    #returns an array of pods
    
    @staticmethod
    def GetServicesByStatefulSet(apiClient : client.CoreV1Api, clusterName : str, namespace : str) :

        response = apiClient.list_namespaced_service(
            namespace = namespace,
            label_selector = 'release={}'.format(clusterName)
        )

        return response.items
    
    @staticmethod
    def GetNodes(apiClient : client.CoreV1Api) :

        response = apiClient.list_node()
        return response.items
    

    @staticmethod
    def LabelNode(apiClient : client.CoreV1Api, nodeName : str, labelName : str, labelValue : str) :

        response = apiClient.patch_node(nodeName, {
            "metadata" : {
                "labels" : {
                    labelName : labelValue
                }
            }
        })

        return response
    
    @staticmethod
    def GetNamespacedPodsByNode(apiClient : client.CoreV1Api, nodeName : str, namespace : str) :
        field_selector = "spec.nodeName={}".format(nodeName)

        response = apiClient.list_namespaced_pod(
            namespace = namespace,
            field_selector = field_selector
        )

        return response.items
    
    @staticmethod
    def GetSvcByNamespace(apiClient : client.CoreV1Api, namespace : str) :

        response = apiClient.list_namespaced_service(namespace = namespace)
        return response.items