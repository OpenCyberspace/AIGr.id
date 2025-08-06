import logging
from queue import Queue
import requests
import os

from .inputs import vDAGInputsListener
from .clients import SearchServerAPI, vDAGDBClient
from .schema import vDAGObject, NodeObject
from .global_tasks import GlobalTasksDB


logger = logging.getLogger(__name__)


def parse_assignment_policy(node: NodeObject):
    try:
        assignment_policy_rule = node.assignmentPolicyRule
        policy_rule_uri = assignment_policy_rule['policyRuleURI']
        parameters = assignment_policy_rule['parameters']

        return {
            "policy_rule_uri": policy_rule_uri,
            "parameters": parameters
        }

    except Exception as e:
        raise e


def run_assignment_for_node(vdag_uri: str, node: NodeObject):
    try:

        data = parse_assignment_policy(node)
        search_api = SearchServerAPI()
        results = search_api.similarity_search(
            policy_rule_uri=data['policy_rule_uri'], parameters=data['parameters']
        )

        if len(results) == 0:
            raise Exception(
                f"no block ID returned for vDAG:{vdag_uri}, node: {node.nodeLabel}")

        if len(results) > 1:
            raise Exception(
                f"more than one block ID returned for vDAG:{vdag_uri}, node: {node.nodeLabel}")

        block = results[0]
        id = block['id']
        return id

    except Exception as e:
        raise e


def get_connection_graph_of_sub_graph(vdag_uri: str):
    try:

        ret, vdag_object = vDAGDBClient().get_vdag(vdagURI=vdag_uri)
        if not ret:
            raise Exception(f"vdag not found: {vdag_object}")

        vdag_assignment_info = vdag_object.assignment_info

        return vdag_assignment_info, vdag_object.graph

    except Exception as e:
        raise e


def compile_graph(type1_graph: dict, node_mapping: dict) -> dict:
    type2_graph = {}
    namewise_mapping_extended = {}

    def process_node_mapping(node_mapping):
        expanded_mapping = {}
        for node_label, block_id in node_mapping.items():
            if isinstance(block_id, str) and block_id.startswith("vdag:::"):
                vdag_uri = block_id.split(":::", 1)[1]
                try:
                    sub_node_mapping, sub_graph = get_connection_graph_of_sub_graph(
                        vdag_uri)
                    sub_compiled_graph = compile_graph(
                        sub_graph, sub_node_mapping)

                    # Merge sub-graph into main graph
                    type2_graph.update(sub_compiled_graph["graph"])
                    expanded_mapping[node_label] = sub_compiled_graph["head"]

                except Exception as e:
                    logging.error(f"Failed to fetch sub-vDAG {vdag_uri}: {e}")
            else:
                expanded_mapping[node_label] = block_id
        return expanded_mapping

    expanded_node_mapping = process_node_mapping(node_mapping)

    for block_id in expanded_node_mapping.values():
        if block_id not in type2_graph:
            type2_graph[block_id] = []

    for connection in type1_graph.get("connections", []):
        dest_label = connection["nodeLabel"]
        dest_block = expanded_node_mapping.get(dest_label)

        if dest_block is None:
            logging.warning(
                f"Destination nodeLabel '{dest_label}' not found in mapping.")
            continue

        for inp in connection.get("inputs", []):
            src_label = inp["nodeLabel"]
            src_block = expanded_node_mapping.get(src_label)

            if src_block is None:
                logging.warning(
                    f"Source nodeLabel '{src_label}' not found in mapping.")
                continue

            type2_graph[src_block].append(dest_block)

    # Determine head and tail blocks
    all_blocks = set(type2_graph.keys())
    dependent_blocks = {block for deps in type2_graph.values()
                        for block in deps}
    head = (all_blocks - dependent_blocks).pop() if all_blocks - \
        dependent_blocks else None
    tail = [block for block, deps in type2_graph.items() if not deps]

    return {"head": head, "tail": tail, "graph": type2_graph}


def get_connections_graph(api_url, graph_input):

    url = f"{api_url}/discovery/resolve_graph"

    try:
        response = requests.post(url, json=graph_input)
        response_data = response.json()

        if response_data.get("success"):
            return response_data.get("graph")
        else:
            raise Exception(response_data.get(
                "message", "Unknown error occurred"))

    except requests.exceptions.RequestException as e:
        raise Exception(f"Request error: {e}")


def compile_graph_stage_2(input_graph: dict):
    try:

        api_url = os.getenv("ADHOC_INFERENCE_API_URL",
                            "http://localhost:20000")

        # use adhoc inference service to obtain the connections graph:
        connections_info = get_connections_graph(
            api_url, graph_input=input_graph)
        return connections_info

    except Exception as e:
        raise e


def map_vdag_to_blocks(vdag_object: vDAGObject):
    vdag_client = vDAGDBClient()
    vdag_uri = vdag_object.vdagURI

    logger.info(f"received vDAG object = {vdag_object.to_dict()}")

    try:
        # Check if vDAG already exists
        vdag_exists, existing_vdag = vdag_client.get_vdag(vdag_uri)
        if vdag_exists:
            status = existing_vdag.status
            if status in ["pending", "failed"]:
                vdag_client.delete_vdag(vdag_uri)
                logger.info(
                    f"Deleted existing vDAG with URI {vdag_uri} in {status} state.")
            elif status in ["active", "assigned"]:
                raise Exception(
                    f"vDAG with URI {vdag_uri} already exists with status {status}.")

        assignment_info = {}
        for node in vdag_object.nodes:
            try:

                if node.nodeType == "block" or node.nodeType == "":

                    if node.manualBlockId != "":
                        assignment_info[node.nodeLabel] = node.manualBlockId
                    else:
                        block_id = run_assignment_for_node(vdag_uri, node)
                        assignment_info[node.nodeLabel] = block_id
                else:
                    assignment_info[node.nodeLabel] = "vdag:::" + node.vdagURI
            except Exception as e:
                logger.error(f"Failed to assign node {node.nodeLabel}: {e}")
                vdag_object.status = "failed"
                vdag_client.create_vdag(vdag_object)
                raise Exception(f"Assignment failed for node {node.nodeLabel}")

        logging.info(f"vdag_uri: {vdag_uri}, mapping: {assignment_info}")

        # compile graph:
        type_2_graph = compile_graph(
            vdag_object.graph, node_mapping=assignment_info)
        type_3_graph = compile_graph_stage_2(type_2_graph["graph"])

        rev_connections = {}
        for nodeLabel, block_id in assignment_info.items():
            rev_connections[block_id] = nodeLabel

        vdag_object.compiled_graph_data = {
            "head": type_2_graph['head'],
            "tail": type_2_graph['tail'],
            "t2_graph": type_2_graph['graph'],
            "t3_graph": type_3_graph,
            "rev_mapping": rev_connections
        }

        # All nodes successfully assigned
        vdag_object.status = "assigned"
        vdag_object.assignment_info = assignment_info
        vdag_client.create_vdag(vdag_object)
        logger.info(
            f"vDAG {vdag_uri} successfully assigned with mapping: {assignment_info}")
        return assignment_info

    except Exception as e:
        logger.error(f"Error in mapping vDAG {vdag_uri} to blocks: {e}")
        raise e


def search_dry_run(vdag_object: vDAGObject):

    vdag_uri = vdag_object.vdagURI
    try:

        assignment_info = {}

        for node in vdag_object.nodes:
            try:
                if node.nodeType == "block" or node.nodeType == "":

                    if node.manualBlockId != "":
                        assignment_info[node.nodeLabel] = node.manualBlockId
                    else:
                        block_id = run_assignment_for_node(vdag_uri, node)
                        assignment_info[node.nodeLabel] = block_id
                else:
                    assignment_info[node.nodeLabel] = "vdag:::" + node.vdagURI
            except Exception as e:
                logger.error(f"Failed to assign node {node.nodeLabel}: {e}")
                vdag_object.status = "failed"
                raise Exception(f"Assignment failed for node {node.nodeLabel}")

        return assignment_info

    except Exception as e:
        raise e


def map_vdag_to_blocks_dry_run(vdag_object: vDAGObject):
    vdag_client = vDAGDBClient()
    vdag_uri = vdag_object.vdagURI

    logger.info(f"received vDAG object = {vdag_object.to_dict()}")

    try:
        # Check if vDAG already exists
        vdag_exists, existing_vdag = vdag_client.get_vdag(vdag_uri)
        if vdag_exists:
            status = existing_vdag.status
            if status in ["pending", "failed"]:
                vdag_client.delete_vdag(vdag_uri)
                logger.info(
                    f"Deleted existing vDAG with URI {vdag_uri} in {status} state.")
            elif status in ["active", "assigned"]:
                raise Exception(
                    f"vDAG with URI {vdag_uri} already exists with status {status}.")

        assignment_info = {}
        for node in vdag_object.nodes:
            try:

                if node.nodeType == "block" or node.nodeType == "":

                    if node.manualBlockId != "":
                        assignment_info[node.nodeLabel] = node.manualBlockId
                    else:
                        block_id = run_assignment_for_node(vdag_uri, node)
                        assignment_info[node.nodeLabel] = block_id
                else:
                    assignment_info[node.nodeLabel] = "vdag:::" + node.vdagURI
            except Exception as e:
                logger.error(f"Failed to assign node {node.nodeLabel}: {e}")
                raise Exception(f"Assignment failed for node {node.nodeLabel}")

        # compile graph:
        type_2_graph = compile_graph(
            vdag_object.graph, node_mapping=assignment_info)
        type_3_graph = compile_graph_stage_2(type_2_graph["graph"])

        rev_connections = {}
        for nodeLabel, block_id in assignment_info.items():
            rev_connections[block_id] = nodeLabel

        compiled_graph_data = {
            "head": type_2_graph['head'],
            "tail": type_2_graph['tail'],
            "flat_graph": type_2_graph['graph'],
            "connections_graph": type_3_graph,
            "rev_mapping": rev_connections
        }

        return {
            "nodesAssignmentInfo": assignment_info,
            "graph": compiled_graph_data
        }

    except Exception as e:
        raise e


def dry_run_graph(vdag_object: vDAGObject):
    try:
        vdag_uri = vdag_object.vdagURI
        assignment_info = {}
        for node in vdag_object.nodes:
            try:

                if node.nodeType == "block" or node.nodeType == "":

                    if node.manualBlockId != "":
                        assignment_info[node.nodeLabel] = node.manualBlockId
                    else:
                        block_id = run_assignment_for_node(vdag_uri, node)
                        assignment_info[node.nodeLabel] = block_id
            except Exception as e:
                logger.error(f"Failed to assign node {node.nodeLabel}: {e}")
                raise Exception(f"Assignment failed for node {node.nodeLabel}")

        # compile graph L2
        compiled_info = compile_graph(vdag_object.graph, assignment_info)
        return compiled_info

    except Exception as e:
        raise e


class vDAGProcessor:
    def __init__(self, internal_queue: Queue):
        self.internal_queue = internal_queue
        self.global_tasks_db = GlobalTasksDB()

    def start(self):
        logger.info("Starting vDAGProcessor...")
        while True:
            try:
                task_id, vdag_object = self.internal_queue.get()
                if vdag_object is None:
                    logger.info("Received shutdown signal.")
                    break
                logger.info(
                    f"Processing vDAGObject with URI {vdag_object.vdagURI}.")
                assignment_info = map_vdag_to_blocks(vdag_object)
                self.internal_queue.task_done()

                # update status data in tasks DB:
                self.global_tasks_db.update_task(
                    task_id, "completed", task_status_data=assignment_info
                )

            except Exception as e:
                logger.error(f"Error processing vDAGObject: {e}")
                self.internal_queue.task_done()


class DryRunner:

    @staticmethod
    def DryRunAssignmentPolicy(input_data: dict):
        try:

            vdag_object = vDAGObject.from_dict(input_data)
            assignment_info = search_dry_run(vdag_object)

            return assignment_info

        except Exception as e:
            raise e

    @staticmethod
    def DryRunEndToEnd(input_data: dict):
        try:

            vdag_object = vDAGObject.from_dict(input_data)
            dry_run_result = map_vdag_to_blocks_dry_run(vdag_object)
            return dry_run_result

        except Exception as e:
            raise e

    @staticmethod
    def ValidateGraph(input_data: dict):
        try:

            vdag_object = vDAGObject.from_dict(input_data)
            validated_graph = dry_run_graph(vdag_object)

            return validated_graph

        except Exception as e:
            raise e


def start_listeners(api_server):
    try:
        internal_queue = Queue()
        listener = vDAGInputsListener(internal_queue)
        processor = vDAGProcessor(internal_queue)

        api_server()

        listener.start()
        processor.start()
    except Exception as e:
        logger.error(e)
