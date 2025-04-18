import os
import yaml

FOLDER_PATH = "./registries"  # Change to the path of your folder
NAMESPACE = "registries"  # Default namespace (can be overridden per service)
CLUSTER_DOMAIN = "svc.cluster.local"
NODE_IP = "<NODE_PUBLIC_IP>"  # Replace with actual node IP or external LB

def collect_services_from_yaml(yaml_file):
    services = []
    with open(yaml_file, "r") as f:
        docs = list(yaml.safe_load_all(f))

    for doc in docs:
        if not doc or doc.get("kind") != "Service":
            continue

        metadata = doc.get("metadata", {})
        spec = doc.get("spec", {})
        ports = spec.get("ports", [])

        service_name = metadata.get("name")
        namespace = metadata.get("namespace", NAMESPACE)

        for port_entry in ports:
            node_port = port_entry.get("nodePort")
            if node_port is not None:
                services.append({
                    "name": service_name,
                    "namespace": namespace,
                    "port": port_entry.get("port"),
                    "node_port": node_port
                })
    return services

def main():
    all_services = []

    for file in os.listdir(FOLDER_PATH):
        if file.endswith(".yaml") or file.endswith(".yml"):
            all_services.extend(collect_services_from_yaml(os.path.join(FOLDER_PATH, file)))

    # Sort services by nodePort
    all_services.sort(key=lambda s: s["node_port"])

    # Print the sorted services
    for svc in all_services:
        internal_url = f"http://{svc['name']}.{svc['namespace']}.{CLUSTER_DOMAIN}:{svc['port']}"
        external_url = f"http://{NODE_IP}:{svc['node_port']}"
        print(f"Service: {svc['name']}")
        print(f"  Internal URL : {internal_url}")
        print(f"  External URL : {external_url}")
        print("-" * 60)

if __name__ == "__main__":
    main()
