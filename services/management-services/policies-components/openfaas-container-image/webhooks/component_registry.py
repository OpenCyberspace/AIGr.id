import requests
import os

COMPONENT_REGISTRY_API = os.getenv("COMPONENT_REGISTRY_API")


class ComponentRegistry:

    @staticmethod
    def GetComponentByURI(componentURI: str):
        route = "/getByURI"
        url = COMPONENT_REGISTRY_API + route
        payload = {"uriString": componentURI}

        # get component by URI
        try:
            r = requests.post(url, json=payload)
            if r.status_code != 200:
                raise Exception("Error Code = {}".format(r.status_code))

            data = r.json()
            if data['error']:
                raise Exception(data['payload'])

            if type(data['payload']) == list and len(data['payload']) == 0:
                raise Exception("{} not found".format(componentURI))

            return True, data['payload'][0]
        except Exception as e:
            return False, e

    @staticmethod
    def GetComponentSize(componentURI: str):
        ret, data = ComponentRegistry.GetComponentByURI(
            componentURI
        )

        print(ret, data)

        if not ret:
            return False, []
        config = data['componentConfig']
        if config['requireFrames']:
            size = config['frameSize']
            sizes_list = []
            for s in size:
                sz_str = "{}x{}".format(s['width'], s['height'])
                if sz_str not in sizes_list:
                    sizes_list.append(sz_str)
            if len(sizes_list) == 0:
                return False, []

            return True, sizes_list
        else:
            return False, []

    @staticmethod
    def GetContainerParams(componentURI: str):
        ret, result = ComponentRegistry.GetComponentByURI(
            componentURI
        )

        if not ret:
            return False, "No container found for {}".format(componentURI)

        return True, result["containerImage"]
