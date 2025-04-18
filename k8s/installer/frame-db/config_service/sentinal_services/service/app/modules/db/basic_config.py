from pymodm import MongoModel, EmbeddedMongoModel, fields


class Discovery(EmbeddedMongoModel) :

    host = fields.CharField(required = True)
    port = fields.IntegerField(required = True)
    password = fields.CharField(required = False)

    #metadata fields, these are not required here
    #for quick access we are maintaining these fields

    clusterServiceHost = fields.CharField(required = True)
    clusterServicePort = fields.IntegerField(required = True)

    #sentinal configuration
    sentinalPassword = fields.CharField(required = False, blank = True)
    sentinalPort = fields.IntegerField(required = False, blank = True)
    sentinalHost = fields.CharField(required = False, blank = False)
    sentinalMasterName = fields.CharField(required = False, blank = False)

    hostAddress = fields.CharField(required = True)

    class Meta:
        final = True


class WorkerConfig(EmbeddedMongoModel) :
    basicConfig = fields.MongoBaseField(required = False)
    class Meta:
        final = True


class BaseRedisStructure(MongoModel) :

    framedbId = fields.CharField(primary_key = True, required = True)
    clusterId = fields.CharField(required = True)
    role = fields.CharField(required = True, choices = ("master", "slave"))
    discovery = fields.EmbeddedDocumentField(model = Discovery, required = True)
    config = fields.EmbeddedDocumentField(model = WorkerConfig, required = False, blank = True)

    #metadata
    class Meta:
        final = True
        collection_name = "basic_config"
    