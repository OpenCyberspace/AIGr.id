curl -X POST http://34.58.1.86:30160/splits/create \
  -H "Content-Type: application/json" \
  -d '{
    "rank_0_cluster_id": "gcp-cluster-2",
    "cluster_id": ["gcp-cluster-2"],
    "deployment_name": "phi-128k-2",
    "nnodes": 4,
    "common_params": {
      "model_name": "microsoft/Phi-3-mini-128k-instruct",
      "image": "34.58.1.86:31280/example/split-runner:latest",
      "master_port": 3000,
    },
    "per_rank_params": [
      {
        "rank": 0,
        "node_id": "wc-gpu-node2",
        "nccl_socket_ifname": "eth0",
        "nvidia_visible_devices": "0",
        "cluster_id": "gcp-cluster-2",
        "cuda_visible_devices": "0"
      },
      {
        "rank": 1,
        "node_id": "wc-gpu-node2",
        "nccl_socket_ifname": "eth0",
        "nvidia_visible_devices": "0,1",
        "cuda_visible_devices": "1",
        "cluster_id": "gcp-cluster-2"
      },
      {
        "rank": 2,
        "node_id": "wc-gpu-node3",
        "nccl_socket_ifname": "eth0",
        "nvidia_visible_devices": "0",
        "cuda_visible_devices": "0",
        "cluster_id": "gcp-cluster-2"
      },
      {
        "rank": 3,
        "node_id": "wc-gpu-node3",
        "nccl_socket_ifname": "eth0",
        "nvidia_visible_devices": "1",
        "cuda_visible_devices": "0,1",
        "cluster_id": "gcp-cluster-2"
      }
    ],
    "multi_cluster": false,
    "platform": "torch"
  }'
