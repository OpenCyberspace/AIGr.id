from .configs import settings
settings.load_config_at_startup()

#logging
import logging
logging = logging.getLogger("MainLogger")

logging.info("Wrote logs")

from fastapi import FastAPI

app = FastAPI()

#register routers here 
from .health import healthRouter

app.include_router(healthRouter, prefix = "/health", tags = ['utils'])