from ..aios_logger import AIOSLogger, ErrorSeverity
import requests
import json

class Actions:

    @staticmethod
    def update_params(cluster_svc: str, payload: dict, lgr: AIOSLogger):
        try:
            data = json.dumps(payload)
            if TEST_MODE_URL == "":
                raise Exception("Merger can only run with TEST_MODE_URL set")

            URL = cluster_svc + "/api/submitTask"

            result = requests.post(URL, json={
                "action": "update_parameters",
                "payload": data
            })

            if result.status_code != 202:

                res_data = result.json()

                raise Exception(
                    "MDAG router exception, code={}, trace={}".format(
                        result.status_code, res_data
                    )
                )

            lgr.info(
                action="infra_create",
                message="Submitted Task to master-dag controller",
                extras={"payload": payload}
            )

            return True, result.json()

        except Exception as e:
            lgr.error(
                action="infra_create",
                message="Failed to make request",
                severity=ErrorSeverity.HIGH,
                exception=e,
                extras={"payload": payload}
            )
            return False, e
