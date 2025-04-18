from pymodm import MongoModel, EmbeddedMongoModel, fields


class AlertsConfig :

    clusterId = fields.CharField(required = True)
    

    class Meta :
        final = True 
        collection_name = "alerts_config"