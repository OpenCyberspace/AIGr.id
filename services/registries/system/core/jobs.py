import requests
import logging

import os
import pymongo
from pymongo.errors import PyMongoError
from typing import Optional, List
from dataclasses import dataclass, field, asdict
from typing import Dict


class JobsSubmittorClient:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.create_job_endpoint = f"{self.api_url}/create_job"

    def submit_job(self, name: str, policy_rule_uri: str, job_id: str,
                   policy_rule_parameters: dict = None,
                   node_selector: dict = None,
                   inputs: dict = None) -> dict:

        payload = {
            "name": name,
            "policy_rule_uri": policy_rule_uri,
            "job_id": job_id,
            "policy_rule_parameters": policy_rule_parameters or {},
            "node_selector": node_selector or {},
            "inputs": inputs or {}
        }

        try:
            logging.info("Submitting job to create_job endpoint.")
            response = requests.post(self.create_job_endpoint, json=payload)
            response.raise_for_status()
            logging.info(f"Job '{name}' submitted successfully.")
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error submitting job: {e}")
            return {"success": False, "message": str(e)}


@dataclass
class PolicyJobs:
    job_id: str
    job_output_data: Dict
    job_status: str
    node_id: str
    job_policy_rule_uri: str

    @staticmethod
    def from_dict(data: Dict) -> 'PolicyJobs':
        return PolicyJobs(
            job_id=data['job_id'],
            job_output_data=data['job_output_data'],
            job_status=data['job_status'],
            node_id=data['node_id'],
            job_policy_rule_uri=data['job_policy_rule_uri']
        )

    def to_dict(self) -> Dict:
        return asdict(self)


class PolicyJobsDB:
    def __init__(self):
        try:
            db_url = os.getenv("DB_URL", "mongodb://localhost:27017/policies")
            if not db_url:
                raise ValueError("Environment variable 'DB_URL' is not set.")
            self.client = pymongo.MongoClient(db_url)
            self.db = self.client["policies"]
            self.collection = self.db["policy_jobs"]
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize database connection: {e}")

    def create(self, job: PolicyJobs) -> bool:
        try:
            job_dict = job.to_dict()
            self.collection.insert_one(job_dict)
            return True
        except PyMongoError as e:
            print(f"Error creating job: {e}")
            return False

    def read(self, job_id: str) -> Optional[PolicyJobs]:
        try:
            result = self.collection.find_one({"job_id": job_id})
            if result:
                return PolicyJobs.from_dict(result)
            return None
        except PyMongoError as e:
            print(f"Error reading job: {e}")
            return None

    def update(self, job_id: str, updated_job: PolicyJobs) -> bool:
        try:
            updated_data = updated_job.to_dict()
            result = self.collection.update_one(
                {"job_id": job_id}, {"$set": updated_data}
            )
            return result.matched_count > 0
        except PyMongoError as e:
            print(f"Error updating job: {e}")
            return False

    def delete(self, job_id: str) -> bool:
        try:
            result = self.collection.delete_one({"job_id": job_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"Error deleting job: {e}")
            return False

    def query(self, query_filter: dict) -> List[PolicyJobs]:
        try:
            results = self.collection.find(query_filter)
            return [PolicyJobs.from_dict(result) for result in results]
        except PyMongoError as e:
            print(f"Error executing query: {e}")
            return []
