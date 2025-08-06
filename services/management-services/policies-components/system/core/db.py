import os
import pymongo
from pymongo.errors import PyMongoError
from typing import Optional, List
from .schema import PolicyRule, PolicyExecutors, Function, Graph


class PolicyDB:
    def __init__(self):
        try:
            db_url = os.getenv("DB_URL",  "mongodb://localhost:27017/policies")
            if not db_url:
                raise ValueError("Environment variable 'DB_URL' is not set.")
            self.client = pymongo.MongoClient(db_url)
            self.db = self.client["policies"]
            self.collection = self.db["policies"]
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize database connection: {e}")

    def create(self, policy: PolicyRule) -> bool:
        try:
            policy_dict = policy.to_dict()
            self.collection.insert_one(policy_dict)
            return True
        except PyMongoError as e:
            print(f"Error creating policy: {e}")
            return False

    def read(self, policy_rule_uri: str) -> Optional[PolicyRule]:
        try:
            result = self.collection.find_one(
                {"policy_rule_uri": policy_rule_uri})
            if result:
                return PolicyRule.from_dict(result)
            return None
        except PyMongoError as e:
            print(f"Error reading policy: {e}")
            return None

    def update(self, policy_rule_uri: str, updated_policy: PolicyRule) -> bool:
        try:
            updated_data = updated_policy.to_dict()
            result = self.collection.update_one(
                {"policy_rule_uri": policy_rule_uri}, {"$set": updated_data}
            )
            return result.matched_count > 0
        except PyMongoError as e:
            print(f"Error updating policy: {e}")
            return False

    def delete(self, policy_rule_uri: str) -> bool:
        try:
            result = self.collection.delete_one(
                {"policy_rule_uri": policy_rule_uri})
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"Error deleting policy: {e}")
            return False

    def query(self, query_filter: dict) -> List[PolicyRule]:
        try:
            results = self.collection.find(query_filter)
            return [PolicyRule.from_dict(result) for result in results]
        except PyMongoError as e:
            print(f"Error executing query: {e}")
            return []


class ExecutorsDB:
    def __init__(self):
        try:
            db_url = os.getenv("DB_URL",  "mongodb://localhost:27017/policies")
            if not db_url:
                raise ValueError("Environment variable 'DB_URL' is not set.")
            self.client = pymongo.MongoClient(db_url)
            self.db = self.client["policies"]
            self.collection = self.db["executors"]
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize database connection: {e}")

    def create(self, executor: PolicyExecutors) -> bool:
        try:
            executor_dict = executor.to_dict()
            self.collection.insert_one(executor_dict)
            return True
        except PyMongoError as e:
            print(f"Error creating executor: {e}")
            return False

    def read(self, executor_id: str) -> Optional[PolicyExecutors]:
        try:
            result = self.collection.find_one({"executor_id": executor_id})
            if result:
                return PolicyExecutors.from_dict(result)
            return None
        except PyMongoError as e:
            print(f"Error reading executor: {e}")
            return None

    def update(self, executor_id: str, updated_executor: PolicyExecutors) -> bool:
        try:
            updated_data = updated_executor.to_dict()
            result = self.collection.update_one(
                {"executor_id": executor_id}, {"$set": updated_data}
            )
            return result.matched_count > 0
        except PyMongoError as e:
            print(f"Error updating executor: {e}")
            return False

    def delete(self, executor_id: str) -> bool:
        try:
            result = self.collection.delete_one({"executor_id": executor_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"Error deleting executor: {e}")
            return False

    def query(self, query_filter: dict) -> List[PolicyExecutors]:
        try:
            results = self.collection.find(query_filter)
            return [PolicyExecutors.from_dict(result) for result in results]
        except PyMongoError as e:
            print(f"Error executing query: {e}")
            return []


class FunctionsDB:
    def __init__(self):
        try:
            db_url = os.getenv("DB_URL",  "mongodb://localhost:27017/policies")
            if not db_url:
                raise ValueError("Environment variable 'DB_URL' is not set.")
            self.client = pymongo.MongoClient(db_url)
            self.db = self.client["policies"]
            self.collection = self.db["functions"]
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize database connection: {e}")

    def create(self, function: Function) -> bool:
        try:
            function_dict = function.to_dict()
            self.collection.insert_one(function_dict)
            return True
        except PyMongoError as e:
            print(f"Error creating function: {e}")
            return False

    def read(self, function_id: str) -> Optional[Function]:
        try:
            result = self.collection.find_one({"function_id": function_id})
            if result:
                return Function.from_dict(result)
            return None
        except PyMongoError as e:
            print(f"Error reading function: {e}")
            return None

    def update(self, function_id: str, updated_function: Function) -> bool:
        try:
            updated_data = updated_function.to_dict()
            result = self.collection.update_one(
                {"function_id": function_id}, {"$set": updated_data}
            )
            return result.matched_count > 0
        except PyMongoError as e:
            print(f"Error updating function: {e}")
            return False

    def delete(self, function_id: str) -> bool:
        try:
            result = self.collection.delete_one({"function_id": function_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"Error deleting function: {e}")
            return False

    def query(self, query_filter: dict) -> List[Function]:
        try:
            results = self.collection.find(query_filter)
            return [Function.from_dict(result) for result in results]
        except PyMongoError as e:
            print(f"Error executing query: {e}")
            return []


class GraphsDB:
    def __init__(self):
        try:
            db_url = os.getenv("DB_URL",  "mongodb://localhost:27017/policies")
            if not db_url:
                raise ValueError("Environment variable 'DB_URL' is not set.")
            self.client = pymongo.MongoClient(db_url)
            self.db = self.client["policies"]
            self.collection = self.db["graphs"]
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize database connection: {e}")

    def create(self, graph: Graph) -> bool:
        try:
            graph_dict = graph.to_dict()
            self.collection.insert_one(graph_dict)
            return True
        except PyMongoError as e:
            print(f"Error creating graph: {e}")
            return False

    def read(self, graph_uri: str) -> Optional[Graph]:
        try:
            result = self.collection.find_one({"graph_uri": graph_uri})
            if result:
                return Graph.from_dict(result)
            return None
        except PyMongoError as e:
            print(f"Error reading graph: {e}")
            return None

    def update(self, graph_uri: str, updated_graph: Graph) -> bool:
        try:
            updated_data = updated_graph.to_dict()
            result = self.collection.update_one(
                {"graph_uri": graph_uri}, {"$set": updated_data}
            )
            return result.matched_count > 0
        except PyMongoError as e:
            print(f"Error updating graph: {e}")
            return False

    def delete(self, graph_uri: str) -> bool:
        try:
            result = self.collection.delete_one({"graph_uri": graph_uri})
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"Error deleting graph: {e}")
            return False

    def query(self, query_filter: dict) -> List[Graph]:
        try:
            results = self.collection.find(query_filter)
            return [Graph.from_dict(result) for result in results]
        except PyMongoError as e:
            print(f"Error executing query: {e}")
            return []
