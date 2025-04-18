from .configs import settings
settings.load_config_at_startup()

import logging

logging = logging.getLogger("MainLogger")

from fastapi import FastAPI
from .modules.health import healthRouter
from .modules.discovery import discoveryRouter
from .modules.configuration import configurationRouter

app = FastAPI()

#api for service health-endpoint
app.include_router(healthRouter, prefix = "/health", tags = ["utils"])

#apis for discovery of master and slaves
app.include_router(discoveryRouter, prefix = "/discovery", tags = ['discovery'])

#apis for configuring sentinels 
app.include_router(configurationRouter, prefix = "/config", tags = ['config'])