import pymodm
import os

from source_mapping import *

MONGO_URI = os.getenv("FRAMEDB_MAPPING_URI")
pymodm.connect("{}/framedb?authSource=admin".format(
    MONGO_URI
))

db = FrameSourceMapping(
    source
)
