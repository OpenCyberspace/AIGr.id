import subprocess
import os
import shlex
import shutil
import tarfile, zipfile
from typing import ClassVar
from .env import POLICY_RULES_ROOT_DIR, PIP_INSTALLER, POLICY_RULE_CLASS_NAME, POLICY_RULE_DOWNLOAD_PATH, POLICY_RULE_REMOTE_URL
import sys
import requests
import requests


class ModuleNotFoundException(Exception):
    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.path = path
    
    def __str__(self) -> str:
        return "path {} not found".format(self.path)

class ModuleLoadException(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
    
    def __str__(self) -> str:
        return "path {} not found".format(self.reason)


def install_modules(path):
    args = "{} install -r {}".format(PIP_INSTALLER, path)
    args = shlex.split(args)

    # call a sub-process
    child_handle = subprocess.Popen(args, stdout=subprocess.PIPE)
    _ = child_handle.communicate()[0]

    exit_code = child_handle.returncode
    if exit_code != 0:
        raise ModuleLoadException("failed to install dependencies for policy rule {}".format(path))
    

def prepare_module(resolved_path):

    print('resolved path: ', resolved_path)
    
    try:
        sub_paths = os.listdir(resolved_path)
        pkg_name = None
        print('sub paths: ', sub_paths)
        for sub_path in sub_paths:
            if sub_path != "__pycache__":
                pkg_name = sub_path
                break
        else:
            raise ModuleLoadException("no root directory found in the provided package")

        resolved_path = os.path.join(resolved_path, pkg_name)
        sys.path.append(resolved_path)

        print('Resolved path: ', resolved_path)

        requirements_file = os.path.join(resolved_path, 'requirements.txt')
        if os.path.exists(requirements_file):
            install_modules(requirements_file)

        # append to sys paths
        for entry in os.path.join(resolved_path):
            abs_path = os.path.join(resolved_path, entry)
            # is a directory?
            if os.path.isdir(abs_path):
                sys.path.append(abs_path)
                requirements_file = os.path.join(abs_path, 'requirements.txt')
                if os.path.exists(requirements_file):
                    install_modules(requirements_file)
        
        # import root package:
        package = __import__(pkg_name)
        policy_rule_class = getattr(package, POLICY_RULE_CLASS_NAME)

        return policy_rule_class

    except Exception as e:
        raise ModuleLoadException(str(e))


def download_module(url: str) -> str:
    
    tar_file_name = url.split("/")[-1]
    if not tar_file_name.endswith('.tar.gz'):
        tar_file_name = tar_file_name + '.tar.gz'

    path = os.path.join(tar_file_name)

    with requests.get(url, stream=True) as download_handle:
        download_handle.raise_for_status()
        with open(path, 'wb') as file_target:
            for chunk in download_handle.iter_content(chunk_size=8192):
                file_target.write(chunk)

    return path 


def load_module_from_local_path(id: str, path: str):

    # is this a URL?
    if path.startswith('http'):
        path = download_module(path)

    #1. check if path exists
    if not os.path.exists(path):
        raise ModuleNotFoundException(path)
    
    if not os.path.exists(POLICY_RULES_ROOT_DIR):
        os.makedirs(POLICY_RULES_ROOT_DIR)
    
    # is it a tar file or module path
    resolved_final_path = None
    if path.endswith(".tar.gz") or path.endswith('.tar') or path.endswith('.tar.xz'):
        # extract tar file to the rules directory
        policy_root = os.path.join(POLICY_RULES_ROOT_DIR, id)
        if not os.path.exists(policy_root):
            os.mkdir(policy_root)
        else:
            shutil.rmtree(policy_root)
            os.mkdir(policy_root)
        
        with tarfile.open(path) as handle:
            handle.extractall(policy_root)
        
        resolved_final_path = policy_root
    elif path.endswith('.zip'):
        policy_root = os.path.join(POLICY_RULES_ROOT_DIR, id)
        if not os.path.exists(policy_root):
            os.mkdir(policy_root)
        else:
            shutil.rmtree(policy_root)
            os.mkdir(policy_root)
        
        with zipfile.open(path) as handle:
            handle.extractall(policy_root)

        resolved_final_path = policy_root
    else:
        resolved_final_path = path
    
    return prepare_module(resolved_final_path)

def load_policy_rule_from_db(rule_id: str):

    try:
        response = requests.post(POLICY_RULE_REMOTE_URL + "/rules/get", json={
            "rule_uri": rule_id
        })

        data = response.json()
        if not data['success']:
            raise Exception(data['message'])
        data = data['rule_data']
        return data['code'], data['rule_schema']['settings'], data['rule_schema']['parameters']       

    except Exception as e:
        print(e)
        return False, str(e), None

