from heapq import heappop, heappush
from typing import Dict, List, Tuple, Any


# NOTE: These are intentionally simplified, educational placeholders.
# They return path-like simulated outputs so the UI can consume AI behavior
# before connecting real city graph data.


def breadth_first_search(graph: Dict[Any, List[Any]], start: Any, goal: Any) -> List[Any]:
    """Basic BFS path finder over an unweighted graph."""
    if start == goal:
        return [start]

    queue: List[Tuple[Any, List[Any]]] = [(start, [start])]
    visited = {start}

    while queue:
        node, path = queue.pop(0)
        for neighbor in graph.get(node, []):
            if neighbor in visited:
                continue
            if neighbor == goal:
                return path + [neighbor]
            visited.add(neighbor)
            queue.append((neighbor, path + [neighbor]))

    return []


def depth_first_search(graph: Dict[Any, List[Any]], start: Any, goal: Any) -> List[Any]:
    """Basic DFS path finder."""
    if start == goal:
        return [start]

    stack: List[Tuple[Any, List[Any]]] = [(start, [start])]
    visited = set()

    while stack:
        node, path = stack.pop()
        if node in visited:
            continue
        visited.add(node)

        for neighbor in graph.get(node, []):
            if neighbor == goal:
                return path + [neighbor]
            stack.append((neighbor, path + [neighbor]))

    return []


def a_star_search(
    graph: Dict[Any, List[Tuple[Any, float]]],
    start: Any,
    goal: Any,
    heuristic: Dict[Any, float],
) -> List[Any]:
    """Simplified A* using adjacency list with edge weights."""
    open_heap: List[Tuple[float, float, Any, List[Any]]] = []
    heappush(open_heap, (heuristic.get(start, 0.0), 0.0, start, [start]))

    best_cost = {start: 0.0}

    while open_heap:
        _, g_cost, node, path = heappop(open_heap)
        if node == goal:
            return path

        for neighbor, edge_cost in graph.get(node, []):
            new_cost = g_cost + edge_cost
            if new_cost < best_cost.get(neighbor, float('inf')):
                best_cost[neighbor] = new_cost
                f_cost = new_cost + heuristic.get(neighbor, 0.0)
                heappush(open_heap, (f_cost, new_cost, neighbor, path + [neighbor]))

    return []
