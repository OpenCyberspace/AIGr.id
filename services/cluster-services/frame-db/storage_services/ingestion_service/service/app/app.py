from fastapi import FastAPI
from .completion import completionRouter
from .apis import jobsRouter
from .health import healthRouter
import logging
from .configs import settings
settings.load_settings()

logging = logging.getLogger("MainLogger")


#import routers


app = FastAPI()

# route for health
app.include_router(healthRouter, prefix="/health", tags=['utils'])

# route for jobs APIs
app.include_router(jobsRouter, prefix="/jobs", tags=['jobs'])

# route to notify job completion
app.include_router(completionRouter, prefix='/completedJobs', tags=['jobs'])
