from ..configs import settings
from fastapi import APIRouter
from .utils import with_logging, send_success_message

healthRouter = APIRouter()

@with_logging("/health/ping")
@healthRouter.get("/ping")
async def ping() :
    return send_success_message({"message" : "pong!"})

