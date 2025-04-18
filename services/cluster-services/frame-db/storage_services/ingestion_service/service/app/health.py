from .configs import settings
from fastapi import APIRouter, Request
from .utils import with_logging, send_success_message

import logging
logging = logging.getLogger("MainLogger")

healthRouter = APIRouter()


def log_request(request : Request, dictPayload : dict = None) :

    url = request.url.path
    logging.info(
        "{} got hit".format(url), 
        extra = {
            "client_host" : request.client.host,
            "client_port" : request.client.port,
            "payload" : str(dictPayload) if dictPayload else None,
            "endpoint" : url
        }
    )

@with_logging("/health/ping")
@healthRouter.get("/ping")
async def ping(request : Request) :
    log_request(request)
    return send_success_message({"message" : "pong!"})

