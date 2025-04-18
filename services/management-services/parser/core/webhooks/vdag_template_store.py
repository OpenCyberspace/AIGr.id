import requests
import os

vDAG_TEMPLATE_STORE_API_URL = os.getenv("vDAG_TEMPLATE_STORE_API_URL")


class vDAGSpecStoreAPI:

    @staticmethod
    def mk_get(params, route):
        try:
            URL = vDAG_TEMPLATE_STORE_API_URL + route
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
    def GetvDAGSTemplateByURI(id: str):
        try:

            route = "/getByURI"
            ret, response = vDAGSpecStoreAPI.mk_get({"vdagURI": id})
            if not ret:
                raise Exception(str(response))

            return True, response

        except Exception as e:
            return False, str(e)


class TemplateAPIClient:
    def __init__(self):
        self.base_url = os.getenv("TEMPLATES_STORE_API_URL")

    def execute_template_policy(self, template_uri, input_data=None, parameters=None):
        url = f"{self.base_url}/template/execute"
        payload = {
            "template_uri": template_uri,
            "input_data": input_data or {},
            "parameters": parameters or {}
        }
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            return data.get("data")
        else:
            error_data = response.json()
            raise Exception(error_data.get("error", "Unknown error"))
