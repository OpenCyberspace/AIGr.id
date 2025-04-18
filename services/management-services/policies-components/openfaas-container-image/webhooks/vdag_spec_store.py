import requests
import os

vDAG_SPEC_STORE_API_URL = os.getenv("vDAG_SPEC_STORE_API_URL")


class vDAGSpecStoreAPI:

    @staticmethod
    def mk_get(params, route):
        try:
            URL = vDAG_SPEC_STORE_API_URL + route
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
    def GetvDAGSpecObjectById(id: str):
        try:

            route = "/getByURI"
            ret, response = vDAGSpecStoreAPI.mk_get({"vdagURI": id})
            if not ret:
                raise Exception(str(response))
            
            return True, response


        except Exception as e:
            return False, str(e)
