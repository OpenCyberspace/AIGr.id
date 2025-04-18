import os

# init all the ENV variables once

# which pip manager to use
PIP_INSTALLER = os.getenv("PIP_INSTALLER", "pip3")

# system pacakges caching path
PIP_PACKAGE_CACHE = os.getenv("PIP_CACHE_PATH", "/tmp")

# python core pacakages path
POLICY_RULES_ROOT_DIR = os.getenv("POLICY_RULES_ROOT_DIR", ".")

# core policy rule name
POLICY_RULE_CLASS_NAME = "AIOSv1PolicyRule"

# temp download path
POLICY_RULE_DOWNLOAD_PATH = "/tmp"
POLICY_RULE_REMOTE_URL = os.getenv("POLICY_RULE_REMOTE_URL", "http://localhost:2000")
