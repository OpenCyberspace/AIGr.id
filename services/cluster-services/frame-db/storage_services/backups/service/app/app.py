from .configs import settings
settings.load_settings()

import logging
logging = logging.getLogger("MainLogger")


#import routers
from .health import healthRouter
from .apis import backupsRouter

from fastapi import FastAPI


app = FastAPI()

#route for health
app.include_router(healthRouter, prefix = "/health", tags = ['utils'])

#route for backup and restore
app.include_router(backupsRouter, prefix = "/backup", tags = ['backups'])