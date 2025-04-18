from pymodm import MongoModel, EmbeddedMongoModel, fields


'''
This is a useful metadata collection that will help us in 
deriving insights to large types of queries and quick updates in case 
of failures. We will be adding more fields to this collection as and when it demands.
'''


class FramedbToSource :

    framedb = fields.CharField(required = True, primary_key = True)
    sources = fields.EmbeddedDocumentListField(model = fields.CharField(), required = False, default = [], blank = True)
    nodeTag = fields.CharField(required = True)


