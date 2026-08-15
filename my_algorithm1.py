import sys
from steiner_graph import steiner_graph as sg
import BCR_solver
import HYP_solver
from collections import deque, defaultdict
from steiner_graph import other_endpoint
import copy
import itertools as itt
import networkx as nx

def my_algorithm_1(graph: sg):
    root = graph.terminals[0]
    demand_pathes = get_demand_pathes(graph, root)    # BCRの最適解から要求パスの一覧を取得
    demand_path_keys = list(demand_pathes.keys())

    def synthesizability_check(current_synthesized, to_synthesize_idx):
        if demand_path_keys[current_synthesized[0]][-1] != demand_path_keys[to_synthesize_idx][-1]:
            return False    # ルートに入るアークが一致しない
        
        new_path_vertices = set()
        for arc_idx in demand_path_keys[to_synthesize_idx]:
            new_path_vertices.add(graph.arcs[arc_idx]["u"])

        exist_cycle = False
        for current_path_idx in current_synthesized:    # 合成しようとしているパスのルート以外の頂点が、すでに合成しているパスにも含まれた場合、サイクルができるので合成しない
            splitted = False
            for arc_idx in reversed(demand_path_keys[current_path_idx]):
                if graph.arcs[arc_idx]["u"] not in new_path_vertices:
                    splitted = True
                if splitted and graph.arcs[arc_idx]["u"] in new_path_vertices:
                    exist_cycle = True
                    break
            if exist_cycle:
                break

        return not exist_cycle

    def synthesize_pathes(current_synthesized):
        component_arcs = []
        component_other_terminals = []
        for current_path_idx in current_synthesized:
            path = demand_path_keys[current_path_idx]
            component_arcs.extend(path)
            component_other_terminals.append(demand_pathes[path]["source"][0])
        component_arcs = tuple(set(component_arcs))

        component_cost = 0
        for arc_idx in component_arcs:
            component_cost += graph.arcs[arc_idx]["cost"]

        component_root = demand_pathes[demand_path_keys[current_synthesized[0]]]["root"]

        return component_arcs, component_root, component_other_terminals, component_cost

    def construct_D_p(current_root):
        D_p = nx.DiGraph()
        current_HYP_components = HYP_components.copy()
        for path in demand_path_keys:
            path_info = demand_pathes[path]
            if path_info["value"] > 1e-6:
                current_HYP_components[path] = path_info

        y_v = defaultdict(float)
        for component, component_info in current_HYP_components.items():
            for v in component_info["source"]:
                y_v[v] += component_info["value"]
            y_v[component_info["root"]] += component_info["value"]

            for arc_idx in component:
                u, v = graph.arcs[arc_idx]["u"], graph.arcs[arc_idx]["v"]
                if u in graph.steiner_vertices:
                    u = (u, component)
                if v in graph.steiner_vertices or v == component_info["root"]:
                    v = (v, component)
                D_p.add_edge(u, v, capacity = component_info["value"])

            D_p.add_edge((component_info["root"], component), ("t", "special"), capacity = component_info["value"])

        y_R = 0
        for v in graph.terminals:
            y_v[v] -= 1
            y_R += y_v[v]
            D_p.add_edge(("s", "special"), v, capacity = y_v[v])

        D_p.add_edge(current_root, ("t", "special"), capacity = float("inf"))

        return D_p, y_R

    def minimum_slack_from_flow(D_p, y_R, Q_path_idx):
        D_p_Q = D_p.copy()
        for path_idx in Q_path_idx:
            D_p_Q.add_edge(("s", "special"), demand_pathes[demand_path_keys[path_idx]]["source"][0], capacity = float("inf"))
        flow_capacity, _ = nx.maximum_flow(D_p_Q, ("s", "special"), ("t", "special"))

        return flow_capacity - y_R - 1

    current_base_path_idx = 0
    HYP_components = {}
    HYP_cost = 0

    while True:    # 危険なSのスラックを検査し、すべて正であれば合成
        current_base_path = demand_path_keys[current_base_path_idx]
        if demand_pathes[current_base_path]["value"] < 1e-6:
            current_base_path_idx += 1
            if current_base_path_idx == len(demand_path_keys):
                break
            continue    # まだ合成しなければならないパスのうち最初のものを合成元とする

        current_root = demand_pathes[demand_path_keys[current_base_path_idx]]["root"]
        D_p, y_R = construct_D_p(current_root)
        current_synthesized = [current_base_path_idx]    # 現在合成済みのパスのリスト
        slack_capacity = float("inf")
        minimum_demand = demand_pathes[current_base_path]["value"]

        for to_synthesize_idx in range(current_base_path_idx + 1, len(demand_path_keys)):    #合成できるパスをすべて合成する
            if not synthesizability_check(current_synthesized, to_synthesize_idx):    # 合成してコンポーネントの条件を満たさないならスキップ
                continue
            
            synthesizable = True
            minimum_slack = float("inf")
            for synthesized_idx in current_synthesized:
                minimum_slack = min(minimum_slack, minimum_slack_from_flow(D_p, y_R, (synthesized_idx, to_synthesize_idx)))
                if minimum_slack < 1e-6:    # 危険なSのどれかのスラックが0ならスキップ
                    synthesizable = False
                    break

            if synthesizable:
                slack_capacity = min(slack_capacity, minimum_slack)    # 後で合成量を決めるときのために、Qが始点2個の組のときの結果は保持しておく
                minimum_demand = min(minimum_demand, demand_pathes[demand_path_keys[to_synthesize_idx]]["value"])
                current_synthesized.append(to_synthesize_idx)

        for i in range(3, len(current_synthesized) + 1):
            minimum_slack = float("inf")
            for pathes in itt.combinations(current_synthesized, i):
                minimum_slack = min(minimum_slack, minimum_slack_from_flow(D_p, y_R, pathes))
            slack_capacity = min(slack_capacity, minimum_slack / (i-1))

        synthesize_amount = min(slack_capacity, minimum_demand)

        for synthesized_idx in current_synthesized:
            demand_pathes[demand_path_keys[synthesized_idx]]["value"] -= synthesize_amount
        synthesized_component, component_root, component_other_terminals, component_cost = synthesize_pathes(current_synthesized)
        component_info = HYP_components.setdefault(synthesized_component, {})
        component_info["value"], component_info["root"], component_info["source"] = synthesize_amount, component_root, component_other_terminals
        HYP_cost += synthesize_amount * component_cost

    return {
        "gained_value": HYP_cost,
        "components": HYP_components
    }

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
    pathes_from_flow = {}

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
                path_info = pathes_from_flow.setdefault(key, {})
                path_info["value"], path_info["root"], path_info["source"] = path_info.get("value", 0) + path_capacity, graph.arcs[idx]["v"], [graph.arcs[decomposited_path[0]]["u"]]
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
    demand_pathes = {}

    for s in graph.terminals:
        if s == root:
            continue
        pathes_from_flow = unit_flow_decomposition(graph, capacity, s, root)
        for path, path_info in pathes_from_flow.items():
            current_info = demand_pathes.setdefault(path, {})
            current_info["value"] = max(demand_pathes[path].get("value", 0), path_info["value"])
            current_info["root"], current_info["source"] = path_info["root"], path_info["source"]

    return demand_pathes    # キーはパス(アークのタプル)、値は{"value": 要求量, "root": 終点, "source": 始点}

if __name__ == "__main__":
    graph = sg()
    graph.graph_from_json("examplegraph1.json")
    graph.validate()
    graph.graph_plot()
    result = my_algorithm_1(graph)
    HYP_components, HYP_cost = result["components"], result["gained_value"]
    for component, component_info in HYP_components.items():
        component_arcs = set()
        component_cost = 0
        for arc_idx in component:
            arc = graph.arcs[arc_idx]
            component_arcs.add((arc["u"], arc["v"]))
            component_cost += arc["cost"]
        print(f"x: {component_info["value"]}, cost: {component_cost}, component: {component_arcs}")
    print(f"gained value: {HYP_cost}")