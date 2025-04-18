from init_container import execute_init_container
from init_container.k8s import HelmManager, HelmSubprocess, K8sUtils

class SampleContainerClass:
    def __init__(self, envs, block_data, cluster_data, k8s, operating_mode="create"):
        self.envs = envs
        self.block_data = block_data
        self.cluster_data = cluster_data
        self.operating_mode = operating_mode
        self.k8s = k8s

    def begin(self):
        # Perform initialization logic here
        return True, "Initialization successful."

    def main(self):
        # Perform main execution logic here
        return True, "Main execution successful."

    def finish(self):
        # Perform finalization logic here
        return True, "Finalization successful."


if __name__ == "__main__":
    execute_init_container(SampleContainerClass)
