import os 

KUBEFILE_PATH="/root/.kube"

def load_settings():

    global KUBEFILE_PATH
    KUBEFILE_PATH = os.getenv("KUBEFILE_PATH", "/root/.kube")

    print(KUBEFILE_PATH)
