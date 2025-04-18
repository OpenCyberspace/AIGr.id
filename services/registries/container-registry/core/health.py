import requests
import logging

logger = logging.getLogger(__name__)

def is_healthy(url: str, timeout: int = 5) -> bool:
    
    try:
        response = requests.get(f"{url.rstrip('/')}/v2/", timeout=timeout)
        logger.info(f"Connection to Docker registry at {url} successful with status code: {response.status_code}")
        return True
    except requests.RequestException as e:
        logger.error(f"Unable to reach Docker registry at {url}: {e}")
        raise Exception(f"Connection to Docker registry failed: {e}")

def get_health_check_data(url: str, timeout: int = 5) -> dict:
   
    try:
        response = requests.get(f"{url.rstrip('/')}/v2/", timeout=timeout)
        return {
            "reachable": True,
            "status_code": response.status_code,
            "reason": response.reason,
            "url": url
        }
    except requests.RequestException as e:
        logger.error(f"Health check connection failed for {url}: {e}")
        raise Exception(f"Registry is not reachable at {url}: {e}")
