from pymodm import fields, MongoModel, EmbeddedMongoModel


# this is the schema definition for mongodb mapping
# source_id : ID of the frame source that generates data
# object : an array of framedb records

class Framedb(EmbeddedMongoModel) :

    serviceIp = fields.CharField(required = True)
    sentinelPort = fields.IntegerField(required = True)
    serviceName = fields.CharField(required = True)

    redisPort = fields.IntegerField(required = True)
    masterIP = fields.CharField(required = True)


class FrameSourceMapping(MongoModel) :

    sourceId = fields.CharField(primary_key = True)
    framedbNodes = fields.EmbeddedDocumentListField(
        model = Framedb
    )

    class Meta :
        final = True
        collection_name = "source_to_db_mapping"

