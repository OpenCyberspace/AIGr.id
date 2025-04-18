from .configs import settings
from fastapi import APIRouter, Request
from .utils import with_logging, send_success_message

import logging
logging = logging.getLogger("MainLogger")

healthRouter = APIRouter()

@with_logging("/health/ping")
@healthRouter.get("/ping")
async def ping(request : Request) :
    print(request.client.host)
    return send_success_message({"message" : "pong!"})

