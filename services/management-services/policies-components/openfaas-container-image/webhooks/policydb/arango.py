from pyArango.connection import *


class ArangoAuth:

    def __init__(self, host, username, password, options={}) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.options = {}


class ArangoDBConnector:

    def __init__(self, auth_object: ArangoAuth):
        self.auth_object = auth_object
        try:
            self.connection = Connection(
                self.auth_object.host,
                self.auth_object.username,
                self.auth_object.password,
                loadBalancing=self.auth_object.options.get(
                    "load_balancing", "round-robin"),
                use_grequests=self.auth_object.options.get(
                    "use_grequests", False),
                use_jwt_authentication=False,
                max_retries=self.auth_object.options.get("max_retries", 5),
                max_conflict_retries=self.auth_object.options.get(
                    "max_conflict_retries", 5)
            )
        except Exception as e:
            raise e

    def create_db(self, db_name, kwargs):
        try:
            return self.connection.createDatabase(db_name, **kwargs)
        except Exception as e:
            raise e

    def create_collection(self, db, collection, kwargs):
        try:
            return db.createCollection(collection, **kwargs)
        except Exception as e:
            raise e

    def get_db(self, db_name):
        try:
            return self.connection[db_name]
        except Exception as e:
            raise e

    def get_collection(self, db_name, collection_name):
        try:
            return self.get_db(db_name)[collection_name]
        except Exception as e:
            raise e

    def remove(self, collection, key):
        try:
            del collection[key]
        except Exception as e:
            raise e

    def get(self, collection, key):
        try:
            return collection[key]
        except Exception as e:
            raise e

    def put(self, collection, object):
        try:

            doc = collection.createDocument()
            for key, value in object.items():
                doc[key] = value

            doc.save()

        except Exception as e:
            raise e

    def get_entries(self, collection, keys):
        try:
            entries = []
            for key in keys:
                entries.append(collection[key])

            return entries

        except Exception as e:
            raise e

    def execute_aql(self, db_name, query, batch_size=100, raw_results=True):
        try:

            db = self.get_db(db_name)
            query_result = db.AQLQuery(
                query, batch_size=batch_size, raw_results=raw_results)

            rows = []
            for result in query_result:
                rows.append(result)

            return result

        except Exception as e:
            raise e
