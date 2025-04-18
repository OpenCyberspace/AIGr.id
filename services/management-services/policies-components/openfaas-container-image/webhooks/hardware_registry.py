import requests
import os

HARDWARE_REGISTRY_API = os.getenv("HARDWARE_REGISTRY_API")


class HardwareRegistryAPI:

    @staticmethod
    def mk_post(payload, route):
        try:
            URL = HARDWARE_REGISTRY_API + route
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
            URL = HARDWARE_REGISTRY_API + route
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
    def CreateNewMachine(payload):
        try:

            route = "/machines/createNewMachine"
            ret, result = HardwareRegistryAPI.mk_post(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def RemoveMachine(payload):
        try:

            route = "/machines/removeMachine"
            ret, result = HardwareRegistryAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def UpdateMachineInfo(payload):
        try:

            route = "/machines/updateMachine"
            ret, result = HardwareRegistryAPI.mk_post(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def UpdateMachineState(payload):
        try:

            route = "/machines/updateMachineState"
            ret, result = HardwareRegistryAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetMachineById(payload):
        try:

            route = "/machines/getMachineById"
            ret, result = HardwareRegistryAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetMachineByURI(payload):
        try:

            route = "/machines/getMachineByURI"
            ret, result = HardwareRegistryAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def CreateNewResource(payload):
        try:

            route = "/resources/createNewResource"
            ret, result = HardwareRegistryAPI.mk_post(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def RemoveResource(payload):
        try:

            route = "/resources/removeResource"
            ret, result = HardwareRegistryAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def UpdateResourceInfo(payload):
        try:

            route = "/resources/updateResource"
            ret, result = HardwareRegistryAPI.mk_post(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def UpdateResourceState(payload):
        try:

            route = "/resources/updateResourceState"
            ret, result = HardwareRegistryAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetResourceById(payload):
        try:

            route = "/resources/getResourceById"
            ret, result = HardwareRegistryAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)

    @staticmethod
    def GetResourceByURI(payload):
        try:

            route = "/resources/getResourceByURI"
            ret, result = HardwareRegistryAPI.mk_get(payload, route)
            if not ret:
                raise Exception(e)

            return True, result

        except Exception as e:
            return False, str(e)
