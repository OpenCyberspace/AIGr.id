# AIGrid for Developers and Creators

## ✨ What Can You Do with OpenOS?

- Connect Kubernetes clusters into a **global compute network**
- Deploy your AI models (like LLMs or vision models) as reusable **Blocks**
- Deploy **multiple blocks on same GPU** to save resources
- Define workflows using **vDAGs** (virtual Directed Acyclic Graphs)
- Share and re-use **models, data, blocks and compute infrastructure**
- Use **Python policies** to control how the network behaves
- Extend your Blocks with third-party tools via init containers
- Collect and use **metrics** to make smart decisions and observe the network

---

## 🧰 Key Features

| Feature             | What It Means                                     |
|---------------------|---------------------------------------------------|
| 🌍 Global Clustering | Connect clusters into a unified network           |
| ⚙️ Smart Scheduling  | Run AI tasks where resources are available        |
| 🛠️ Python Policies   | Use Python scripts to control the system          |
| 🧱 Modular Blocks     | Reusable building blocks for AI                   |
| 🧠 Split LLMs        | Run parts of a model across machines              |
| 🧪 GPU Sharing       | Run multiple jobs on the same GPU                 |
| 🔗 Distributed Graphs | Define workflows across blocks and clusters |
| 📦 Plug in Tools     | Bring your own frameworks, models, or services    |
| 📡 Send Tasks Easily  | Submit tasks through gRPC APIs                   |
| 🔍 Observe Everything| Track system performance with metrics             |


For the detailed breakdown of features [visit this link](https://docs.aigr.id/#breakdown-of-features)

---

## 🚀 **Getting Started**


| 🧩 **Essentials**          |
|---------------------------|
| [AIGrid component semantic diagram](./stack_bd.md) |
| [AIGrid component writeup](./stack_writeup.md) |
| [Paper](https://resources.aigr.id)  |
| [Concepts](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/getting-started/concepts.md)  |
| [Architecture](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/arch.md)  |
| 🧭 **User Flow Guides**    |
| [Network Creator & Admin Flow](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/getting-started/userflow-network.md)  |
| [Cluster Contributor & Admin Flow](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/getting-started/userflow-cluster.md)  |
| [Node Contributor Flow](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/getting-started/useflow-node.md)  |
| [Block Creator Flow](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/getting-started/userflow-block.md)  |
| [vDAG Creator Flow](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/getting-started/useflow-vdag.md)  |
| [End User (Inference Task Submitter) Flow](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/getting-started/userflow-inference.md)  |
| ⚙️ **Installation**         |
| [Network Creation](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/installation/installation.md)  |
| [Onboarding Cluster](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/onboarding-notes/onboarding-cluster.md)  |
| [Onboarding Node to a Cluster](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/onboarding-notes/onboarding-node.md)  |



---

## 🚀 Quickstart

1. [Creating a network ](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#creating-a-new-network)

- [Create your own network](tutorial/tutorial.md#creating-a-new-network)
- [Add clusters and nodes](tutorial/tutorial.md#joining-a-cluster-to-an-existing-network)
- [Deploy AI models](tutorial/tutorial.md#steps-to-deploy-a-block)
- [Connect external systems](tutorial/tutorial.md#deploying-external-system-along-with-the-block-using-init-containers)
- [Split and run large models across multiple GPUs](tutorial/tutorial.md#splitting-llms-and-deploying-them-across-the-network-as-a-vdag)

3. [Joining a node to an already existing cluster](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#joining-a-node-to-an-already-existing-cluster)

4. [Simple block deployment across multiple GPUs (Reference model considered: Mistral7B LLM)](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#simple-block-deployment-across-multiple-gpus-reference-model-considered-mistral7b-llm)

5. [Simple block deployment on a single GPU (Sample model considered: YOLOv5](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#simple-block-deployment-on-a-single-gpu-sample-model-considered-yolov5)

6. [Linking an externally deployed vLLM system to the block for serving](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#deploying-a-vdag-and-submitting-inference-tasks-to-the-vdag)

7. [Deploying a vDAG and submitting inference tasks to the vDAG](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#deploying-a-vdag-and-submitting-inference-tasks-to-the-vdag)

## 📚 Learn More

| Section | Link |
|--------|------|
| 📄 Concept Overview | [Concepts](getting-started/concepts.md) |
| 🧭 How It Works | [Architecture](arch.md) |
| 🛠️ Setup Instructions | [Installation Guide](installation/installation.md) |
| 🧪 Tutorials | [Quickstart](tutorial/tutorial.md) |
| 🗂️ User Guides | [User Flows](getting-started/userflow-network.md) |