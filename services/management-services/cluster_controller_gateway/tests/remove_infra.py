import requests, os, yaml

kubepath = os.path.join(
    os.getenv("HOME"), ".kube/config"
)

config = yaml.load(open(kubepath))

request_data = {
    "kube_config_data": config,
    "cluster_id": "cluster-123"
}

response = requests.post("http://127.0.0.1:5000/remove-cluster-infra", json=request_data)

print(response.json())