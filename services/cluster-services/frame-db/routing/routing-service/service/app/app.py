from .configs import settings
settings.load_config_at_startup()

import logging
logging = logging.getLogger("MainLogger")


#import routers
from .apis import routingService
from .health import healthRouter
from .back_preassure import backpreassureRouter

from fastapi import FastAPI

app = FastAPI()

#route for health
app.include_router(healthRouter, prefix = "/health", tags = ['utils'])

#routes for CRUD
app.include_router(routingService, prefix = "/routing", tags = ['routing'])

#routes for back-preassure control
app.include_router(backpreassureRouter, prefix = "/backpressure", tags = ['back-preassure'])
