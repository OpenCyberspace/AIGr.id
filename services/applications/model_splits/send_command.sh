curl -X POST http://localhost:5000/splits/create \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_id": ["gcp-cluster-2"],
    "deployment_name": "phi-128k",
    "nnodes": 2,
    "common_params": {
      "model_name": "microsoft/Phi-3-mini-128k-instruct",
      "image": "34.58.1.86:31280/example/split-runner:latest",
      "master_port": 3000
    },
    "per_rank_params": [
      {
        "rank": 0,
        "node_id": "wc-gpu-node3",
        "nccl_socket_ifname": "eth0",
        "nvidia_visible_devices": "0"
      },
      {
        "rank": 1,
        "node_id": "wc-gpu-node1",
        "nccl_socket_ifname": "eth0",
        "nvidia_visible_devices": "0"
      }
    ],
    "multi_cluster": false,
    "platform": "torch"
  }'
