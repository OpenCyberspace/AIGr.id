from .schema import Graph, Function
from .db import GraphsDB, FunctionsDB
from .executor_proxy import ExecutorProxyClient
from collections import defaultdict, deque


def is_dag(graph_connection_data: dict) -> bool:

    in_degree = defaultdict(int)
    adjacency_list = defaultdict(list)

    for src, targets in graph_connection_data.items():
        for tgt in targets:
            adjacency_list[src].append(tgt)
            in_degree[tgt] += 1
            if src not in in_degree:
                in_degree[src] = 0

    queue = deque([node for node in in_degree if in_degree[node] == 0])
    visited_count = 0

    while queue:
        node = queue.popleft()
        visited_count += 1
        for neighbor in adjacency_list[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return visited_count == len(in_degree)


def execute_graph(graph_uri: str, input_data: dict) -> dict:

    try:
        graph = GraphsDB().read(graph_uri)
        if not graph:
            raise Exception(f"Graph with URI '{graph_uri}' not found.")

        graph_connection_data = graph.graph_connection_data
        graph_function_ids = graph.graph_function_ids

        if not is_dag(graph_connection_data):
            raise Exception(
                "Graph is not a Directed Acyclic Graph (DAG). Execution stopped.")

        all_nodes = set(graph_function_ids)
        outgoing_nodes = set(
            node for src in graph_connection_data for node in graph_connection_data[src])
        leaf_nodes = list(all_nodes - outgoing_nodes)

        if len(leaf_nodes) != 1:
            raise Exception(
                "Graph must have exactly one leaf node to produce a single final output.")
        leaf_node = leaf_nodes[0]

        in_degree = defaultdict(int)
        adjacency_list = defaultdict(list)

        for src, targets in graph_connection_data.items():
            for tgt in targets:
                adjacency_list[src].append(tgt)
                in_degree[tgt] += 1
                if src not in in_degree:
                    in_degree[src] = 0

        queue = deque(
            [node for node in graph_function_ids if in_degree[node] == 0])
        function_outputs = {}

        while queue:
            current_function_id = queue.popleft()

            function = FunctionsDB().read(current_function_id)
            if not function:
                raise Exception(
                    f"No function with ID '{current_function_id}' found.")

            # Fetch executor URI
            executor_host_uri = function.function_executor_uri
            if not executor_host_uri:
                raise Exception(
                    f"Executor URI not specified for function '{current_function_id}'.")

            client = ExecutorProxyClient(base_url=executor_host_uri)

            inputs = []
            for src, targets in graph_connection_data.items():
                if current_function_id in targets:
                    inputs.append(function_outputs.get(src, input_data))
            if len(inputs) == 1:
                inputs = inputs[0]

            # Call the function
            result = client.call_function(current_function_id, inputs)
            function_outputs[current_function_id] = result

            for neighbor in adjacency_list[current_function_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return function_outputs[leaf_node]

    except Exception as e:
        raise Exception(f"Error executing graph: {str(e)}")
