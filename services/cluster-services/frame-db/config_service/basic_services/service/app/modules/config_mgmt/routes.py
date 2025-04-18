from ...configs import settings
import logging
logging = logging.getLogger("MainLogger")

from fastapi import APIRouter, Request
from ..utils import with_logging, validate_json_fields, send_success_message, send_error_message

from .basic import BasicRedisConfig

from ..test_connection import generate_test_connection


def log_request(request : Request, dictPayload : dict = None) :

    url = request.url.path
    logging.info(
        "{} got hit".format(url), 
        extra = {
            "client_host" : request.client.host,
            "client_port" : request.client.port,
            "payload" : str(dictPayload) if dictPayload else None,
            "endpoint" : url
        }
    )

#initialize the app in test mode if settings.TEST=True
test_connection = None 
test_mode = False

if settings.TEST :
    test_mode = True
    test_connection = generate_test_connection()

    logging.info("Starting all controllers in test mode, set TEST=No in production")


basicConfigRouter = APIRouter()
basicConfigController = BasicRedisConfig(test_mode, test_connection)


@with_logging('/config/basic/getConfig')
@basicConfigRouter.post('/getConfig')
async def getConfig(body: dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['configName', 'framedb_id'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = basicConfigController.getConfig(body['framedb_id'] ,body['configName'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging('/config/basic/setConfig')
@basicConfigRouter.post('/setConfig')
async def setConfig(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['configName', 'value', 'framedb_id'])
    if not ret :
        return send_error_message("Missing field " +  field)
    
    ret, result = basicConfigController.setConfig(body['framedb_id'], body['configName'], body['value'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging('/config/basic/getConfigsInfo')
@basicConfigRouter.get('/getConfigsInfo')
async def getConfigsInfo(request : Request) :
    log_request(request)

    ret, result = basicConfigController.getConfigsAvailable()
    if not ret :
        return send_error_message(result)
    return send_success_message(result)

@with_logging('/config/basic/getConfigsByCategory')
@basicConfigRouter.post('/getConfigsByCategory')
async def getConfigsByCategory(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['categoryName'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = basicConfigController.getConfigsByCategory(category = body['categoryName'])
    if not ret :
        return send_error_message(result)
    return send_success_message(result)



#snapshots router
from .snapshots import BackupsAndSnapshotController

snapshotsController = BackupsAndSnapshotController(test_mode, test_connection)
snapshotsRouter = APIRouter()

@with_logging("/config/snapshots/getSnapshotsConfig")
@snapshotsRouter.post("/getSnapshotsConfig")
async def getSnapshotConfig(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['framedb_id'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = snapshotsController.getBackupConfig(body['framedb_id'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/config/snapshots/setSnapshotInterval")
@snapshotsRouter.post("/setSnapshotInterval")
async def getSnapshotConfig(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['framedb_id', 'interval', 'n_keys_changed'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = snapshotsController.setBackupConfig(body['framedb_id'], body['interval'], body['n_keys_changed'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/config/snapshots/setRDBName")
@snapshotsRouter.post("/setRDBName")
async def getSnapshotConfig(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['framedb_id', 'dbname'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = snapshotsController.setRDBFileName(body['framedb_id'], body['dbname'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/config/snapshots/setRDBCompression")
@snapshotsRouter.post("/setRDBCompression")
async def getSnapshotConfig(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['framedb_id', 'enable'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = snapshotsController.setRDBCompression(body['framedb_id'], body['enable'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/config/snapshots/setRDBChecksum")
@snapshotsRouter.post("/setRDBChecksum")
async def getSnapshotConfig(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['framedb_id', 'enable'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = snapshotsController.setRDBChecksum(body['framedb_id'], body['enable'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)

@with_logging("/config/snapshots/takeSnapshot")
@snapshotsRouter.post("/takeSnapshot")
async def getSnapshotConfig(body : dict, request : Request) :
    log_request(request, body)
    ret, field = validate_json_fields(body, ['framedb_id'])
    if not ret :
        return send_error_message("Missing field " + field)
    
    ret, result = snapshotsController.takeSnapshot(body['framedb_id'], body['as_file'] if 'as_file' in body else None)
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


#logging router
from .logging import LogsController
loggingRouter = APIRouter()

logsController = LogsController(test_mode, test_connection)

@with_logging("/config/logs/getSlowLog")
@loggingRouter.post("/getSlowLog")
async def getSlowLog(body : dict, request : Request) :
    log_request(request, body)
    ret, fields = validate_json_fields(body, ['framedb_id', 'n_records'])
    if not ret :
        return send_error_message("Missing field " + fields)
    
    ret, result = logsController.getSlowLog(body['framedb_id'], body['n_records'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)


from ..db.restore_config import ConfigRestorer
restoreRouter = APIRouter()

@with_logging("/config/restore/restoreConfig")
@restoreRouter.post("/restoreConfig")
def restoreConfig(body: dict, request : Request):
    log_request(request, body)
    ret, fields = validate_json_fields(body, ['framedb_id'])
    if not ret :
        return send_error_message("Missing field " + fields)
    
    ret, result = ConfigRestorer().restoreConfigs(body['framedb_id'])
    if not ret :
        return send_error_message(result)
    
    return send_success_message(result)