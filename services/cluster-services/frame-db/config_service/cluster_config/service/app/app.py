from .configs import settings
settings.load_config_at_startup()

from fastapi import FastAPI

import logging
logging = logging.getLogger("MainLogger")

from .scaling import replicasRouter
from .cluster import clusterRouter
from .nodes import nodesRouter
from .health import healthRouter

app = FastAPI()

#api for health
app.include_router(healthRouter, prefix = "/health", tags = ['utils'])

#apis for replication 
app.include_router(replicasRouter, prefix = "/replication", tags = ['replication'])

#apis for cluster creation and removal
app.include_router(clusterRouter, prefix = "/cluster", tags = ['cluster'])

#apis for node labelling
app.include_router(nodesRouter, prefix = "/node", tags = ['node'])
