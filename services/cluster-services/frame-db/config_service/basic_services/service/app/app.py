from .configs import settings
settings.load_config_at_startup()

#logging configuration
import logging
#from .log_config import config
logging = logging.getLogger("MainLogger")

from fastapi import FastAPI
from .modules.health import healthRouter
from .modules.config_mgmt.routes import basicConfigRouter, loggingRouter, snapshotsRouter, restoreRouter

app = FastAPI()

#register routes
app.include_router(healthRouter, prefix = "/health", tags = ["utils"])

#basic configs routes
app.include_router(basicConfigRouter, prefix = "/config/basic", tags = ['config'])

#snapshots routes
app.include_router(snapshotsRouter, prefix = "/config/snapshots", tags = ['snapshots'])

#logging routes
app.include_router(loggingRouter, prefix = "/config/logs", tags = ['logs'])

#config restore routes
app.include_router(restoreRouter, prefix = "/config/restore", tags = ['restore'])
