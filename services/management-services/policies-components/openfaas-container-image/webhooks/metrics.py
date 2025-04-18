import requests
import os

HARDWARE_METRICS_COLLECTOR_URI = os.getenv("HARDWARE_METRICS_COLLECTOR_URI")
METRICS_SIDECAR_URI = os.getenv("METRICS_SIDECAR_URI")


class HardwareMetricsCollectorAPI:

    @staticmethod
    def mk_post(payload, route):
        try:
            URL = HARDWARE_METRICS_COLLECTOR_URI + route
            response = requests.post(URL, json=payload)
            if response.status_code != 200:
                raise Exception(
                    "Server error, failed to make Request code={}".format(
                        response.status_code
                    )
                )

            data = response.json()
            if data['error']:
                raise Exception(data['message'])

            return True, data['response']

        except Exception as e:
            return False, e

    @staticmethod
    def execute_query_on_machines(payload):
        try:

            machines = []
            queries = {}

            for entry in payload:
                machines.append(entry['machineId'])
                queries[entry['machineId']] = queries.get(entry['machineId'], []).append(
                    entry['query']
                )

            ret, result = HardwareMetricsCollectorAPI.mk_post({
                "machines": machines,
                "queries": queries,
            })

            if not ret:
                return False, str(e)

            return True, result

        except Exception as e:
            return False, str(e)


class BlockMetricsCollectorAPI:

    @staticmethod
    def mk_post(payload, route):
        try:
            URL = HARDWARE_METRICS_COLLECTOR_URI + route
            response = requests.post(URL, json=payload)
            if response.status_code != 200:
                raise Exception(
                    "Server error, failed to make Request code={}".format(
                        response.status_code
                    )
                )

            data = response.json()
            if data['error']:
                raise Exception(data['message'])

            return True, data['response']

        except Exception as e:
            return False, e

    @staticmethod
    def mk_get(params, route):
        try:
            URL = HARDWARE_METRICS_COLLECTOR_URI + route
            response = requests.get(URL, params=params)
            if response.status_code != 200:
                raise Exception(
                    "Server error, failed to make Request code={}".format(
                        response.status_code
                    )
                )

            data = response.json()
            if data['error']:
                raise Exception(data['message'])

            return True, data['response']

        except Exception as e:
            return False, e

    @staticmethod
    def CreateNewBlock(payload):
        try:

            route = "/metrics/createNewBlock"
            ret, result = BlockMetricsCollectorAPI.mk_post(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def RemoveBlock(payload):
        try:

            route = "/metrics/removeBlock"
            ret, result = BlockMetricsCollectorAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetBlockMetrics(payload):
        try:

            route = "/metrics/getBlockMetrics"
            ret, result = BlockMetricsCollectorAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetAllClusterBlockMetrics(payload):
        try:

            route = "/metrics/getAllClusterBlockMetrics"
            ret, result = BlockMetricsCollectorAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)


class LocalMetricsCollectorAPI:

    @staticmethod
    def mk_get(params, route):
        try:
            URL = HARDWARE_METRICS_COLLECTOR_URI + route
            response = requests.get(URL, params=params)
            if response.status_code != 200:
                raise Exception(
                    "Server error, failed to make Request code={}".format(
                        response.status_code
                    )
                )

            data = response.json()
            if data['error']:
                raise Exception(data['message'])

            return True, data['response']

        except Exception as e:
            return False, e

    @staticmethod
    def GetLocalBlockMetricsWithoutRefCount():
        try:

            route = "/metrics/getMetricsZeroRefCount"
            ret, response = LocalMetricsCollectorAPI.mk_get(
                params={}, route=route)
            if not ret:
                return False, str(response)

            return True, response

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetLocalBlockMetricsWithoutRefCount1():
        try:

            route = "/metrics/getMetricsZeroRefCount1"
            ret, response = LocalMetricsCollectorAPI.mk_get(
                params={}, route=route)
            if not ret:
                return False, str(response)

            return True, response

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetLocalBlockMetricsWithoutRefCount2():
        try:

            route = "/metrics/getMetricsZeroRefCount2"
            ret, response = LocalMetricsCollectorAPI.mk_get(
                params={}, route=route)
            if not ret:
                return False, str(response)

            return True, response

        except Exception as e:
            return False, str(e)
