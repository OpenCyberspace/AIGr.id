import os
import uuid
import tempfile
import requests
import subprocess
import tarfile
import zipfile
import importlib.util
import sys
import logging
from pathlib import Path
import hashlib
import shutil


logging.basicConfig(level=logging.INFO)


class LocalCodeExecutor:
    def __init__(self, download_url: str, settings: dict, parameters: dict):
        self.download_url = download_url
        self.session_uuid = str(uuid.uuid4())
        self.temp_dir = Path(f"/tmp/{self.session_uuid}")
        self.code_dir = self.temp_dir / "code"
        self.requirements_file = self.code_dir / "requirements.txt"
        self.function_file = self.code_dir / "function.py"
        self.function_class = None
        self.settings = settings
        self.parameters = parameters
        self.cache = {}

    def download(self):
        # Check if the path is a local file or directory
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        target_path = Path(self.download_url)

        print(target_path, target_path.exists())

        if target_path.exists():
            if target_path.is_file() and (target_path.suffix in [".gz", ".zip", ".xz"] or target_path.suffixes[-2:] == [".tar", ".gz"]):
                logging.info(f"Using local archive: {target_path}")
                return target_path
            elif target_path.is_dir():
                logging.info(f"Using local directory: {target_path}")
                self.code_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(target_path, self.code_dir, dirs_exist_ok=True)
                logging.info(f"Copied local directory to {self.code_dir}")
                return None  # No need to unpack or download
            else:
                raise ValueError(
                    "Unsupported local path format or non-existing path")

        # Handle remote downloads
        url_hash = hashlib.md5(self.download_url.encode()).hexdigest()
        if url_hash in self.cache:
            logging.info("Loading from cache")
            cached_path = Path(self.cache.get(url_hash))
            if cached_path.exists():
                return cached_path

        try:
            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()
            archive_path = self.temp_dir / "archive"
            with open(archive_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.cache[url_hash] = str(archive_path)
            logging.info(f"Downloaded and cached file to {archive_path}")
            return archive_path
        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading file: {e}")
            raise

    def unpack(self, archive_path):
        if not archive_path:
            # If archive_path is None, it means the code was copied directly from a directory
            logging.info(
                "No extraction needed (code directory already populated)")
            return

        try:
            if tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path) as tar:
                    tar.extractall(self.temp_dir)
                    logging.info(f"Extracted tar file to {self.temp_dir}")
            elif zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(self.temp_dir)
                    logging.info(f"Extracted zip file to {self.temp_dir}")
            else:
                logging.error("Unsupported file format")
                raise ValueError("Unsupported file format")
            if not self.code_dir.exists():
                raise FileNotFoundError("code/ directory not found in archive")
        except Exception as e:
            logging.error(f"Error extracting archive: {e}")
            raise

    def install_dependencies(self):
        try:
            if self.requirements_file.exists():
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", str(self.requirements_file)])
                logging.info("Installed dependencies from requirements.txt")
            else:
                logging.warning("No requirements.txt found")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error installing dependencies: {e}")
            raise

    def initialize_function(self):
        try:
            spec = importlib.util.spec_from_file_location(
                "function", self.function_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules["function"] = module
            spec.loader.exec_module(module)
            self.function_class = getattr(module, "AIOSv1PolicyRule")(
                "", self.settings, self.parameters)
            logging.info("Initialized AgentSpaceFunction")
        except (AttributeError, FileNotFoundError) as e:
            logging.error(f"Error initializing function: {e}")
            raise

    def evaluate(self, input_data):
        try:
            if not self.function_class:
                raise RuntimeError("Function class not initialized")
            return self.function_class.eval(self.parameters, input_data, None)
        except Exception as e:
            logging.error(f"Error during evaluation: {e}")
            raise

    def init(self):
        try:
            archive_path = self.download()
            self.unpack(archive_path)
            self.install_dependencies()
            self.initialize_function()
        except Exception as e:
            raise e

    def execute(self, input_data):
        try:
            archive_path = self.download()
            self.unpack(archive_path)
            self.install_dependencies()
            self.initialize_function()
            return self.evaluate(input_data)
        except Exception as e:
            logging.error(f"Execution failed: {e}")
            raise
    
    def mgmt(self, action, mgmt_data):
        try:
            return self.function_class.management(action, mgmt_data)
        except Exception as e:
            raise e
