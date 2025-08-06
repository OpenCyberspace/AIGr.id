from .schema import Graph, Function
from .db import GraphsDB, FunctionsDB
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


