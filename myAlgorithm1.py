import sys
from steiner_graph import steiner_graph as sg
import BCR_solver
import HYP_solver
from collections import deque
from steiner_graph import other_endpoint

def my_algorithm_1(graph: sg):
    root = graph.terminals[0]
    BCR_result = BCR_solver(graph, root)
    demand_pathes = []
    for i in range(1, len(graph.terminals)):
        demand_pathes[i] = maximum_flow(graph, BCR_result["z"], graph.terminals[i], root)

def unit_flow(graph: sg, capacity, s, t):
    if s == t:
        raise ValueError("始点と終点は異なるものを指定してください")
    if len(graph.arcs) != len(capacity):
        raise ValueError("双方向アークの本数とBCRの解の次元が一致しません")
    residual = sg()
    residual.vertices = graph.vertices
    residual.arcs = graph.arcs
    for i in range(len(residual.arcs)):
        residual.arcs[i]["capacity"] = capacity[i]
    residual.build_adjacency
    flow = set()
    while True:
        path, path_capacity = find_path()
        if path is None:
            break

    def find_path():
        visited = {s}
        connect_arcs = {s: None}
        queue = deque([s])
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
        path = set()
        path_capacity = float("inf")
        while connect_arcs[v] is not None:
            path.add(connect_arcs[v])
            path_capacity = min(path_capacity, residual.arcs[connect_arcs[v]]["capacity"])
            v = residual.arcs[connect_arcs[v]]["u"]

        return path, path_capacity

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("JSONファイルを指定してください")
        sys.exit(1)
    graph = sg()
    graph.graph_from_json(sys.argv[1])
    graph.validate()
    graph.graph_plot()