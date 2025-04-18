# 🧠 AIGrid: An Open, Plural, and Polycentric AI Network


AIGrid represents a fundamental shift from siloed, monolithic AI to an **open, plural, and networked AI ecosystem**.

🌐 **AIGr.id** is a polycentric network of independent, plural AI components that coordinate to perform tasks, exchange data, and compose into higher-level intelligence — broader and greater than the sum of its parts.

🧩 Designed as **global public infrastructure for AI**, AIGrid is not owned or controlled by any single entity. It is contributed to and accessed as a digital commons — intelligence built by many, for all.

⚙️ **Powered by [OpenOS.AI](https://openos.ai)** — **A distributed AI Operating System** for open, plural and poly-centric AI networks.

**OpenOS.AI is 100% open source and community-driven.**

---

> 💡 *AIGrid is infrastructure for a future where intelligence is networked, composable, shared and plural by design.*

---


 📘 **Product Deep Dive**: Discover the philosophy, design, strategy, and purpose behind this platform in our in-depth write-up.  
👉 [Read the full write-up](https://aigridpaper.pages.dev)

---


> **Disclaimer**: The modules of this component have been unit tested, and integration tests between services have been completed. However, this project is still in beta and is not recommended for production use at this time. The testnet is tentatively scheduled for release in the first week of May 2025. For information on upcoming events and roadmap tasks, [refer to this section](#upcoming-activities).

---

**OpenOS.ai** provides full stack AI operations, globally distributed and optimized AI compute scale platform, and data management for decentralized AI networks.

OpenOS.AI enables:
 
- 🧠 **Creation and coordination of multiple cognitive architectures**  
- 🔗 **Composition of modular, networked AI systems**  
- ⚙️ **Dynamic orchestration of distributed AI agents and services**  
- ☁️ **Optimized, cloud-native, and sovereign AI computing at scale**  
- 🎛️ **Actor-controlled resource allocation across shared infrastructure**  
- 🤝 **Shareable AI, compute and data as digital commons and gig-economy for AI** 
- 🗂️ **Distributed data management and flow at massive scale**  
- 🏛️ **Polycentric governance and programmable autonomy**  
- 🌐 **Open, multiplayer AI production and distribution at a global scale**

## Core Features

1. **Unified Network level, Multi-Cluster Resource Pooling**  
   Seamlessly connect Kubernetes clusters and nodes from different geographic locations to form a unified resource pool capable of running any kind of computational workload.

2. **Policy-Driven Infrastructure and Job Management**  
   Use Python-based policies to define and govern the behavior of networks, clusters, and workloads.

3. **Flexible Workload Scheduling**  
   Schedule LLMs, other AI models, or general compute logic — collectively called **Blocks**—on any cluster within the network. Customize scaling, load balancing, and health checks through policies. Workload specifications are defined using a customizable parser format.

4. **Comprehensive, Developer-Friendly SDKs**  
   SDKs are available to help developers write AI model servers or general compute logic for deployment across the network.

5. **Distributed Graph Execution**  
   Define jobs as Directed Acyclic Graphs (DAGs) of Blocks—called **vDAGs**—to build complex workflows that span multiple nodes or clusters.

6. **Third-Party Framework Integration**  
   Port existing frameworks as part of a Block using automated deployment via init containers.

7. **Model Splitting and Distributed Inference**  
   Split large models (e.g., LLMs) into smaller units and deploy them as vDAGs across nodes or clusters, agnostic of the underlying framework.

---

## Breakdown of features:

1. **Global Cluster Networking**  
   Easily connect Kubernetes clusters across regions, forming a globally distributed, policy-governed compute mesh.

2. **Node Onboarding**  
   Add VMs or bare-metal nodes to any cluster within the network, enabling flexible infrastructure expansion.

3. **Custom Rule-Based Orchestration**  
   Write Python policies to control how clusters and networks are formed and how workloads are scheduled, tailored to your specific operational needs.

4. **Python-Native Policy Engine**  
   Policies are written in Python, offering high expressiveness and support for external libraries, enabling complex logic and integration.

5. **Flexible Policy Deployment Modes**  
   Deploy policies as standalone services, ad hoc jobs, or policy graphs, depending on the use case.

6. **Decentralized Registries**  
   Set up and register your own asset or container registries on any cluster. These registries are globally discoverable and shareable within the network.

7. **Block and vDAG Specification via SDKs**  
   Define compute workloads (e.g., LLM inference, object detection, etc.) using the Python SDK. Compose them into vDAGs to form cross-node or cross-cluster workflows. Blocks can be reused across multiple vDAGs.

8. **Sidecar Extensions for Blocks**  
   Extend the functionality of Blocks through customizable sidecar containers.

9. **Resource-Aware Scheduling**  
   Use policies to control resource allocation, auto-scaling, and load balancing. Blocks can scale across nodes and utilize multiple GPUs as needed.

10. **GPU Sharing Across Blocks**  
   Schedule multiple Block instances on the same GPU for efficient resource utilization.

11. **End-to-End Metrics Collection**  
   Collect metrics from Blocks, vDAGs, and nodes. Use them in policy logic for decision-making or define custom metrics as needed.

12. **Policy-Based Auditing and Quotas**  
   Apply policies for vDAG-level audit logging, access controls, and quota management.

13. **Custom Health Checks**  
   Define health check logic using policies for fine-grained monitoring.

14. **gRPC-Based Inference APIs**  
   Submit tasks to Blocks or vDAGs via gRPC-based inference servers.

15. **Multi-Gateway Inference Support**  
   Any user or administrator can deploy their own inference server and register it in a public directory. Each server can enforce its own policies for quotas and access control.

16. **Customizable Specification Format**  
   Define and extend the specification format for onboarding clusters, nodes, Blocks, and vDAGs. Use policies to build custom specification parsers.

17. **Reusable Specification Store**  
   Browse, search, and reuse predefined or customized specifications to quickly deploy Blocks and vDAGs.

18. **Third-Party System Integration**  
   Seamlessly extend Blocks with third-party services or tools, either deployed alongside or externally, automated via init containers.

19. **LLM Splitting and Reusability**  
   Split large LLMs into modular components and distribute them as vDAGs. Each model chunk can be reused across multiple vDAGs, enabling scalable and efficient deployments.

---

## Getting started:

**[Paper](https://resources.aigr.id)**

**[Concepts](getting-started/concepts.md)**

**[Architecture](arch.md)**

**Guides based on user flow:**

  - [Network Creator and Admin flow](getting-started/userflow-network.md)

  - [Cluster Contributor and Cluster admin flow](getting-started/userflow-cluster.md)

  - [Node Contributor flow](getting-started/useflow-node.md)

  - [Block Creator flow](getting-started/userflow-block.md)

  - [vDAG Creator flow](getting-started/useflow-vdag.md)

  - [End user (inference task submitter) flow](getting-started/userflow-inference.md)

**Installation:**

  - [Network Creation](installation/installation.md)

  - [Onboarding Cluster](onboarding-notes/onboarding-cluster.md)
  
  - [Onboarding Node to a cluster](onboarding-notes/onboarding-node.md)


---

## Quickstart tutorial:

[The quickstart tutorial](tutorial/tutorial.md) explains how to:

1. [Creating a network ](tutorial/tutorial.md#creating-a-new-network)

2. [Joining a cluster to an existing network](tutorial/tutorial.md#joining-a-cluster-to-an-existing-network)

3. [Joining a node to an already existing cluster](tutorial/tutorial.md#joining-a-node-to-an-already-existing-cluster)

4. [Simple block deployment across multiple GPUs (Reference model considered: Mistral7B LLM)](tutorial/tutorial.md#simple-block-deployment-across-multiple-gpus-reference-model-considered-mistral7b-llm)

5. [Simple block deployment on a single GPU (Sample model considered: YOLOv5](tutorial/tutorial.md#simple-block-deployment-on-a-single-gpu-sample-model-considered-yolov5)

6. [Linking an externally deployed vLLM system to the block for serving](tutorial/tutorial.md#deploying-a-vdag-and-submitting-inference-tasks-to-the-vdag)

7. [Deploying a vDAG and submitting inference tasks to the vDAG](tutorial/tutorial.md#deploying-a-vdag-and-submitting-inference-tasks-to-the-vdag)

8. [Deploying external system along with the block using init containers](tutorial/tutorial.md#deploying-external-system-along-with-the-block-using-init-containers)

9. [Splitting LLMs and deploying them across the network as a vDAG](tutorial/tutorial.md#splitting-llms-and-deploying-them-across-the-network-as-a-vdag)

---

## Upcoming Activities

1. **Comparison Document**: A detailed comparison between AIOSv1 and Ray/AnyScale – *To be announced*.

2. **Benchmarking and Performance Analysis**: Evaluation of system services, cluster services, block components, and end-to-end benchmarking of popular LLM and non-LLM models on the platform.  
   *(To submit or suggest a model for benchmarking, please open an issue.)* – *To be announced*.

3. **Mainnet Release**: Launch of the mainnet, supporting both public and private deployments – *To be announced*.

4. **Platform Security and IAM**: Implementation of security measures for all platform services, including user IAM using decentralized identity protocols, role-based access control (RBAC), and integration with the policy system for fine-grained security actions – *To be announced*.

5. **Model/Asset Security**: End-to-end security for models and assets, along with enhanced security for policy execution – *To be announced*.

---

## Communications:

1. Email: [community@opencyberspace.org](mailto:community@opencyberspace.org)
2. Discord: [OpenCyberspace](https://discord.gg/W24vZFNB)
3. Twitter: [@opencyberspace](https://x.com/opencyberspace)

---