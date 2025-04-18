from pymodm import fields, EmbeddedMongoModel, MongoModel


class FramedbClusterInfo(MongoModel) :

    cluster_name = fields.CharField(primary_key = True, required = True)
    node_tag = fields.CharField(required = True)
    svc_name = fields.CharField(required = True)
    svc_host = fields.CharField(required = True)
    metrics_svc = fields.CharField(required = True)
    namespace = fields.CharField(required = True)

    master_port = fields.IntegerField(required = True)
    sentinel_port = fields.IntegerField(required = True)
    metrics_port = fields.IntegerField(required = True)

    clusterPods = fields.ListField(field = fields.CharField(), required = False, blank = True, default = [])

    class Meta:
        final = True
        collection_name = "cluster_config"