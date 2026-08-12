import sys
from steiner_graph import steiner_graph as sg
import BCR_solver
import HYP_solver
from collections import deque, defaultdict
from steiner_graph import other_endpoint
import copy

def my_algorithm_1(graph: sg):
    root = graph.terminals[0]

def unit_flow_decomposition(graph: sg, capacity, s, t):
    if s == t:
        raise ValueError("始点と終点は異なるものを指定してください")
    if len(graph.arcs) != len(capacity):
        raise ValueError("双方向アークの本数とBCRの解の次元が一致しません")
    if s not in graph.terminals or t not in graph.terminals:
        raise ValueError("始点と終点はターミナルを指定してください")

    def reverse_arc_idx(idx):
        if idx % 2:
            return idx - 1
        else:
            return idx + 1

    def find_path():
        visited = {s}
        connect_arcs = {s: None}
        queue = deque([s])
        found = False
        while queue:
            u = queue.popleft()
            for idx in residual.arcs_out[u]:
                a = residual.arcs[idx]
                if a["capacity"] > 1e-6:
                    v = a["v"]
                    if v not in visited:
                        visited.add(v)
                        queue.append(v)
                        connect_arcs[v] = idx
                        if v == t:
                            found = True
                            break
            if found:
                break

        if t not in visited:
            return None, None
        v = t
        path = []
        path_capacity = float("inf")
        while connect_arcs[v] is not None:
            path.append(connect_arcs[v])
            path_capacity = min(path_capacity, residual.arcs[connect_arcs[v]]["capacity"])
            v = residual.arcs[connect_arcs[v]]["u"]

        return reversed(path), path_capacity

    residual = sg()
    residual.vertices = graph.vertices
    residual.arcs = copy.deepcopy(graph.arcs)
    for i in range(len(residual.arcs)):
        residual.arcs[i]["capacity"] = capacity[i]
    residual.build_adjacency()
    flow_capacity = 0
    pathes_from_flow = defaultdict(float)

    while True:
        decomposited_path = []
        path, path_capacity = find_path()
        if path is None:
            break
        if flow_capacity + path_capacity > 1:
            path_capacity = 1 - flow_capacity
        for idx in path:
            residual.arcs[idx]["capacity"] -= path_capacity
            residual.arcs[reverse_arc_idx(idx)]["capacity"] += path_capacity
            decomposited_path.append(idx)
            if graph.arcs[idx]["v"] in graph.terminals:
                key = tuple(decomposited_path)
                pathes_from_flow[key] += path_capacity
                decomposited_path = []
        flow_capacity += path_capacity

    if flow_capacity < 1 - 1e-6:
        raise ValueError("単位フローを構築できませんでした")
    return pathes_from_flow

def get_demand_pathes(graph: sg, root = None):
    if root is None:
        root = graph.terminals[0]
    if root not in graph.terminals:
        raise ValueError("rootはターミナルから指定してください")
    result = BCR_solver.BCR_solver(graph, root)
    capacity = result["z"]
    demand_pathes = defaultdict(float)

    for s in graph.terminals:
        if s == root:
            continue
        pathes_from_flow = unit_flow_decomposition(graph, capacity, s, root)
        for path, cost in pathes_from_flow.items():
            demand_pathes[path] = max(demand_pathes[path], cost)

    return demand_pathes

if __name__ == "__main__":
    graph = sg()
    graph.graph_from_json("examplegraph1.json")
    graph.validate()
    graph.graph_plot()
    demand_pathes = get_demand_pathes(graph)
    for path, cost in demand_pathes.items():
        current_path = []
        for idx in path:
            current_path.append((graph.arcs[idx]["u"], graph.arcs[idx]["v"]))
        print(f"cost: {cost}, path: {current_path}")
