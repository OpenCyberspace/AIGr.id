import requests


def is_healthy(public_url):
    try:

        response = requests.get(public_url + "/health")
        response.raise_for_status()

        return True

    except Exception as e:
        raise Exception(f"Asset DB {public_url} is not healthy or not reachable")


def get_health_check_data(public_url):
    try:

        response = requests.get(public_url + "/health")
        response.raise_for_status()

        return response.json()

    except Exception as e:
        raise e
