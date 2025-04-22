# 🧠 **AIGr.id: An Open, Plural, and Polycentric AI Network**

AIGrid represents a fundamental shift from siloed, monolithic AI to an **open, plural, and networked AI ecosystem**.

🌐 **AIGr.id** is a polycentric network of independent, plural AI components that coordinate to perform tasks, exchange data, and compose into higher-level intelligence — broader and greater than the sum of its parts.

🧩 Designed as **global public infrastructure for AI**, AIGrid is not owned or controlled by any single entity. It is contributed to and accessed as a digital commons — intelligence built by many, for all.

⚙️ **Powered by [OpenOS.AI (AIOS)](https://openos.ai)** — **A distributed AI Operating System** for open, plural and poly-centric AI networks.



**OpenOS.AI is 100% open source and community-driven.**

---

 📘 **Product Deep Dive**: Discover the philosophy, design, strategy, and purpose behind this platform in our in-depth write-up.  
👉 [Read the full write-up](https://aigridpaper.pages.dev)

---

<div style="background-color: #f8d7da; color: #721c24; padding: 12px; border-left: 5px solid #f5c6cb; border-radius: 4px; font-size: 90%;">
  <strong>Disclaimer:</strong> The project remains in <strong>beta</strong> and is <strong>not recommended for production use at this time</strong>.
</div>


> While a variant of AIGr.id has been running in production at nearly **500k inferences per second** on bare metal infrastructure in federated setting for close to a year—supporting real-time, sustainable Vision AI workloads—the released version includes significant upgrades to support broader goals, including LLM integration. Although unit and integration tested, this version has **not yet been validated at similar scale or duration**. As such, the project remains in **beta** and is **not recommended for production use at this time**.

<br>

<div style="background-color: #f8f9fa; color: #212529; padding: 12px 16px; border: 1px solid #ced4da; border-radius: 6px; font-size: 90%;">
  <strong>Heads-up:</strong> Testnet is tentatively scheduled for release in the first week of May 2025.  
  For information on upcoming events and roadmap tasks, <a href="https://github.com/OpenCyberspace/AIGr.id?tab=readme-ov-file#-upcoming-activities" style="color: #212529; text-decoration: underline;">refer to this section</a>.
</div>

<br>

---

**OpenOS.AI** provides full stack AI operations, globally distributed and optimized AI compute scale platform, and data management for decentralized AI networks.

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
- 📊 **System-wide observability, behavior tracing, and telemetry**

---

## 🚀 **Core Features Overview**



| 💡 **Feature** | 📘 **Description** |
|----------------|--------------------|
| 🔗 **Unified Network-Level, Multi-Cluster Resource Pooling** | Seamlessly connect Kubernetes clusters from different locations to form a unified resource pool for running any kind of computational workload. |
| ⚙️ **Flexible Resource allocation & Scheduling** | Schedule AI models (LLMs), general compute logic, or custom Blocks on any cluster. Includes customizable scaling, load balancing, and health checks. |
| 🛡️ **Policy-Driven Infrastructure and Job Management** | Govern infrastructure and workloads using Python-based policies for full control over network, cluster, and job behavior. |
| 🔄 **Distributed Graph Execution (vDAGs)** | Define complex workflows as DAGs of Blocks, allowing distributed execution across nodes and clusters. |
| 🧠 **Model Splitting and Distributed Inference** | Break large models (like LLMs) into smaller splits, deploy them as vDAGs across infrastructure, framework-agnostic. |
| 🧰 **Developer-Friendly SDKs** | Use SDKs to easily write and deploy AI model servers or compute logic across the distributed network. |
| 🧩 **Third-Party Framework Integration** | Bring your own stack—wrap existing frameworks and libraries as Blocks using init containers. |
| 🧪 **Multiple Instance Execution / GPU Sharing** | Run multiple Block instances on the same node; a single GPU can be time-shared across multiple instances for maximum efficiency. |
| 📝 **Customizable Parser-Based Workload Definitions** | Define workloads using flexible, pluggable parsers to support different input formats and metadata structures. |
| 📊 **Policy-Based Load Balancing and Health Checks** | Use policy logic to drive runtime decisions for load balancing, instance health, and failover handling. |

---


## 🧩 **Breakdown of Features**

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

## 🚀 **Getting Started**


| 🧩 **Essentials**          |
|---------------------------|
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

## 🧪 **Quickstart Tutorial**:

[The quickstart tutorial](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md) explains how to:

1. [Creating a network ](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#creating-a-new-network)

2. [Joining a cluster to an existing network](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#joining-a-cluster-to-an-existing-network)

3. [Joining a node to an already existing cluster](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#joining-a-node-to-an-already-existing-cluster)

4. [Simple block deployment across multiple GPUs (Reference model considered: Mistral7B LLM)](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#simple-block-deployment-across-multiple-gpus-reference-model-considered-mistral7b-llm)

5. [Simple block deployment on a single GPU (Sample model considered: YOLOv5](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#simple-block-deployment-on-a-single-gpu-sample-model-considered-yolov5)

6. [Linking an externally deployed vLLM system to the block for serving](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#deploying-a-vdag-and-submitting-inference-tasks-to-the-vdag)

7. [Deploying a vDAG and submitting inference tasks to the vDAG](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#deploying-a-vdag-and-submitting-inference-tasks-to-the-vdag)

8. [Deploying external system along with the block using init containers](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#deploying-external-system-along-with-the-block-using-init-containers)

9. [Splitting LLMs and deploying them across the network as a vDAG](https://github.com/OpenCyberspace/OpenOS.AI-Documentation/tree/main/tutorial/tutorial.md#splitting-llms-and-deploying-them-across-the-network-as-a-vdag)

---

## 📅 **Upcoming Activities**

1. **Comparison Document**: A detailed comparison between AIOSv1 and Ray/AnyScale – *To be announced*.

2. **Benchmarking and Performance Analysis**: Evaluation of system services, cluster services, block components, and end-to-end benchmarking of popular LLM and non-LLM models on the platform.  
   *(To submit or suggest a model for benchmarking, please open an issue.)* – *To be announced*.

3. **Mainnet Release**: Launch of the mainnet, supporting both public and private deployments – *To be announced*.

4. **Platform Security and IAM**: Implementation of security measures for all platform services, including user IAM using decentralized identity protocols, role-based access control (RBAC), and integration with the policy system for fine-grained security actions – *To be announced*.

5. **Model/Asset Security**: End-to-end security for models and assets, along with enhanced security for policy execution – *To be announced*.

---

## 📢 Communications

1. 📧 Email: [community@opencyberspace.org](mailto:community@opencyberspace.org)  
2. 💬 Discord: [OpenCyberspace](https://discord.gg/W24vZFNB)  
3. 🐦 X (Twitter): [@opencyberspace](https://x.com/opencyberspace)

---

## 🙋‍♀️ Call for Contributors
 
**AIGrid** is an **open, collaborative project** — and we’re actively looking for contributors who resonate with the mission of building **open, plural, networked AI infrastructure**.

---
 
### 🧠 We Welcome:
 
- **Systems thinkers** & **protocol designers**  
  Help refine the architecture of **polycentric networks**
 
- **Distributed systems engineers**  
  Build and scale the **open execution layer**
 
- **AI/ML developers**  
  Create **interoperable cognitive modules** and **agent topologies**
 
- **Researchers in ethics, governance, trust, alignment, guardrails, incentives, economics**  
  Design and evolve the **policy layers**
 
- **Writers & communicators**  
  Help document, narrate, and **amplify the vision**
 
- **Hackers, tinkerers, visionaries**  
  If this speaks to you — you’re already one of us

---

### 🚀 Whether you want to:
 
- Co-design **AI primitives**
- Propose a **new kind of network**
- Experiment with **governance models**
- Help run a **sovereign AIGrid node, cluster, or network**
 
We’d **love to hear from you.**
 
---
 
### 🔗 Join the Collective  

[**Join our Discord**](https://discord.gg/W24vZFNB)
 
### 📧 Reach Out [community@opencyberspace.org](mailto:community@opencyberspace.org)
 

**Let’s co-create an open & networked AI future — plural, sovereign, and evolving.**

---
