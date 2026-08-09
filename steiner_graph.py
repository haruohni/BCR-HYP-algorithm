from dataclasses import dataclass, field
import json
import random
from collections import deque
import networkx as nx
import itertools as itt

@dataclass
class steiner_graph:    # ターミナル付きグラフ
    vertices: list[str] = field(default_factory = list)
    is_terminal: dict[str,bool] = field(default_factory = dict)
    terminals: list[str] = field(default_factory = list)
    steiner_vertices: list[str] = field(default_factory = list)
    edges: list[dict] = field(default_factory = list)
    arcs: list[dict] = field(default_factory = list)
    adj: dict[str, list[int]] = field(default_factory = dict)
    arcs_in: dict[str, list[int]] = field(default_factory = dict)
    arcs_out: dict[str, list[int]] = field(default_factory = dict)

    def graph_from_json(self, path):    # pathにグラフのJSONファイルを渡す
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vertices = [v["id"] for v in data["vertices"]]
        self.is_terminal = {v["id"]: v["terminal"] for v in data["vertices"]}
        self.terminals = [v["id"] for v in data["vertices"] if v["terminal"] == True]
        self.steiner_vertices = [v["id"] for v in data["vertices"] if v["terminal"] == False]
        self.edges = data["edges"]
        self.arcs = []

        for e in self.edges:
            self.arcs.append({"u": e["u"], "v": e["v"], "cost": e["cost"]})
            self.arcs.append({"u": e["v"], "v": e["u"], "cost": e["cost"]})
            
        self.build_adjacency()

    def graph_random(self, num_terminals, num_steiner_vertices, cost_min = 1, cost_max = 2, edge_prob = 0.3):    # ターミナル、シュタイナー頂点の個数、密度を渡し、辺コストがランダムな連結グラフを生成する
        if num_terminals < 2:
            raise ValueError(f"num_terminals は2以上が必要です: {num_terminals}")
        self.terminals = ["t" + str(i) for i in range(1, num_terminals + 1)]
        self.steiner_vertices = ["s" + str(i) for i in range(1, num_steiner_vertices + 1)]
        self.vertices = self.terminals + self.steiner_vertices
        self.is_terminal = {v: v[0] == "t" for v in self.vertices}
        num_vertices = num_terminals + num_steiner_vertices

        self.edges = []
        connect = self.vertices[:]  # 連結性を担保する
        random.shuffle(connect)
        existing = set()
        for i in range(1, len(connect)):
            u = connect[i]
            v = random.choice(connect[:i])
            self.edges.append({"u": u, "v": v, "cost": random.uniform(cost_min, cost_max)})
            existing.add(frozenset({u,v}))
        for i in range(num_vertices):   #ランダムに辺コストを与える
            for j in range(i+1,num_vertices):
                if frozenset({self.vertices[i],self.vertices[j]}) in existing:
                    continue
                if random.random() < edge_prob:
                    self.edges.append({"u": self.vertices[i], "v": self.vertices[j], "cost": random.uniform(cost_min, cost_max)})

        for e in self.edges:
            self.arcs.append({"u": e["u"], "v": e["v"], "cost": e["cost"]})
            self.arcs.append({"u": e["v"], "v": e["u"], "cost": e["cost"]})

        self.build_adjacency()

    def validate(self):    # 正当性チェック　不適切ならValueErrorを返す
        if len(self.terminals) < 2:
            raise ValueError("ターミナルは2以上必要です")
        
        if len(self.vertices) != len(set(self.vertices)):
            raise ValueError("同じ名前の頂点が存在します")
        
        vertex_set = set(self.vertices)
        for e in self.edges:
            if e["u"] not in vertex_set or e["v"] not in vertex_set:
                raise ValueError("辺の形式が正しくありません")
            if e["u"] == e["v"]:
                raise ValueError("自己ループが存在します")
            if e["cost"] < 0:
                raise ValueError("辺コストは非負である必要があります")
            
        edge_pairs = [frozenset({e["u"], e["v"]}) for e in self.edges]
        if len(edge_pairs) != len(set(edge_pairs)):
            raise ValueError("多重辺が存在します")
        
        if not self.check_terminals_connectivity():
            raise ValueError("ターミナルが非連結です")

    def check_terminals_connectivity(self):
        start = self.vertices[0]
        visited = {start}
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for e_idx in self.adj[u]:
                v = other_endpoint(self.edges[e_idx], u)
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
        return set(self.terminals) <= visited


    def build_adjacency(self):    # 隣接行列, 隣接アークのリストを作成
        self.adj = {v: [] for v in self.vertices}
        for i in range(len(self.edges)):
            if not (self.edges[i] is None):
                self.adj[self.edges[i]["u"]].append(i)
                self.adj[self.edges[i]["v"]].append(i)
        self.arcs_in = {v: [] for v in self.vertices}
        self.arcs_out = {v: [] for v in self.vertices}
        for i in range(len(self.arcs)):
            if not (self.arcs[i] is None):
                self.arcs_in[self.arcs[i]["v"]].append(i)
                self.arcs_out[self.arcs[i]["u"]].append(i)

    def graph_plot(self, path = "graph.png"):   #グラフを描画する
        G = self.to_nxgraph()
        A = nx.nx_agraph.to_agraph(G)
        for v in G.nodes:
            node = A.get_node(v)
            if G.nodes[v]["is_terminal"]:
                node.attr["shape"] = "square"
                node.attr["color"] = "red"
                node.attr["style"] = "filled"
                node.attr["fillcolor"] = "lightcoral"
            else:
                node.attr["color"] = "lightblue"
                node.attr["style"] = "filled"
                node.attr["fillcolor"] = "lightblue"

        for u, v in G.edges:
            edge = A.get_edge(u, v)
            edge.attr["label"] = f"{G.edges[u, v]['cost']:.3f}"

        A.graph_attr["sep"] = "+15"
        A.graph_attr["len"] = "2.0"
        A.graph_attr["size"] = "10,10"
        A.graph_attr["ratio"] = "compress"
        A.graph_attr["dpi"] = "300"
        A.node_attr["fontsize"] = "10"
        A.edge_attr["fontsize"] = "8"
        A.node_attr["width"] = "0.2"
        A.node_attr["height"] = "0.2"
        A.node_attr["fixedsize"] = "true"
        A.layout(prog="neato")    # レイアウト計算（各ノードの座標を決める）
        A.draw(path)    # グラフを描画、画像を保存する

    def to_nxgraph(self):    # networkxのグラフに変換する
        G = nx.Graph()
        for v in self.vertices:
            G.add_node(v, is_terminal = self.is_terminal[v])
        for e in self.edges:
            G.add_edge(e["u"], e["v"], cost = e["cost"])
        return G

    def BCR_plot(self, z_values, path = "BCR_graph.png"):
        if len(z_values) != len(self.arcs):
            raise ValueError("解の次元がアークの本数に一致しません")
        G = self.to_nxgraph_directed(z_values)
        A = nx.nx_agraph.to_agraph(G)
        for v in G.nodes:
            node = A.get_node(v)
            if G.nodes[v]["is_terminal"]:
                node.attr["shape"] = "square"
                node.attr["color"] = "red"
                node.attr["style"] = "filled"
                node.attr["fillcolor"] = "lightcoral"
            else:
                node.attr["color"] = "lightblue"
                node.attr["style"] = "filled"
                node.attr["fillcolor"] = "lightblue"

        for u, v in G.edges:
            cost = G.edges[u, v]["cost"]
            z = G.edges[u, v]["z"]
            edge = A.get_edge(u, v)
            edge.attr["label"] = (
                f'<<font color="black">{cost:.3f}</font>'
                f'<br/><font color="red">{z:.3f}</font>>'
            )
            if z < 1e-6:
                edge.attr["style"] = "invis"

        A.graph_attr["sep"] = "+15"
        A.graph_attr["len"] = "3.0"
        A.graph_attr["size"] = "10,10"
        A.graph_attr["ratio"] = "compress"
        A.graph_attr["dpi"] = "300"
        A.node_attr["fontsize"] = "8"
        A.edge_attr["fontsize"] = "8"
        A.node_attr["width"] = "0.2"
        A.node_attr["height"] = "0.2"
        A.node_attr["fixedsize"] = "true"
        A.layout(prog="neato")    # レイアウト計算（各ノードの座標を決める）
        A.draw(path)    # グラフを描画、画像を保存する

    def to_nxgraph_directed(self, z_values):
        G = nx.DiGraph()
        for v in self.vertices:
            G.add_node(v, is_terminal = self.is_terminal[v])
        for i in range(len(self.arcs)):
            G.add_edge(self.arcs[i]["u"], self.arcs[i]["v"], cost = self.arcs[i]["cost"], z = z_values[i])     
        return G

    def Dreyfus_Wagner(self, terminal_subset):
        G = steiner_graph()    # 指定されていないターミナルを除いたグラフ
        G.terminals = list(terminal_subset)
        G.steiner_vertices = self.steiner_vertices
        G.vertices = G.terminals + G.steiner_vertices
        G.is_terminal = {v: True for v in G.terminals} | {v: False for v in G.steiner_vertices}
        G.edges = [e if (e["u"] in G.vertices and e["v"] in G.vertices) else None for e in self.edges]
        G.build_adjacency()
        if not G.check_terminals_connectivity():    # ターミナルが連結でなければ計算しない
            return None
        shortest_pathes = {u:
                           {
                               v:
                               {
                                   "cost": float("inf"),
                                   "pred_edge": None
                               }
                               for v in G.vertices
                           }
                           for u in G.vertices}
        for u in G.vertices:
            shortest_pathes[u] = G.Dijkstra_all(u)    # Dijkstra法で距離グラフを求めておく

        s, s_v = {}, {}
        for X in itt.combinations(G.vertices, 2):    # DPの基底ケース
            v, w = X[0], X[1]
            X = frozenset(X)
            s[X] = {"cost": shortest_pathes[v][w]["cost"], "X": X, "v": v, "w": w}

        def add_v(X, v):
            return frozenset(X) | {v}

        def set_dif(X, Y):
            return frozenset([v for v in X if v not in Y])
        
        for i in range(2, len(G.terminals)):    # DP本体
            for X in itt.combinations(G.terminals, i):
                X = frozenset(X)
                s_v[X] = {}
                for v in set_dif(G.vertices, X):
                    min_cost = float("inf")
                    min_X_prime = None
                    for j in range(1, i):
                        for X_prime in itt.combinations(X, j):
                            X_prime = set(X_prime)
                            current_cost = s[add_v(X_prime, v)]["cost"] + s[add_v(set_dif(X, X_prime), v)]["cost"]
                            if current_cost < min_cost:
                                min_cost = current_cost
                                min_X_prime = X_prime
                    s_v[X][v] = {"cost": min_cost, "X_prime": min_X_prime}

            for X in itt.combinations(G.terminals, i):
                X = frozenset(X)
                for v in set_dif(G.vertices, X):
                    if add_v(X, v) not in s:
                        min_cost_1 = float("inf")
                        min_w_1 = None
                        for w in X:
                            current_cost = shortest_pathes[v][w]["cost"] + s[X]["cost"]
                            if current_cost < min_cost_1:
                                min_cost_1 = current_cost
                                min_w_1 = w
                        min_cost_2 = float("inf")
                        min_w_2 = None

                        for w in set_dif(G.vertices, X):
                            current_cost = shortest_pathes[v][w]["cost"] + s_v[X][w]["cost"]
                            if current_cost < min_cost_2:
                                min_cost_2 = current_cost
                                min_w_2 = w
                        if min_cost_1 <= min_cost_2:
                            s[add_v(X, v)] = {"cost": min_cost_1, "X": X, "v": v, "w": min_w_1}
                        else:
                            s[add_v(X, v)] = {"cost": min_cost_2, "X": X, "v": v, "w": min_w_2}

        def construct_path(v, w):
            pathes = shortest_pathes[v]
            while pathes[w]["pred_edge"] is not None:
                edge_idx = pathes[w]["pred_edge"]
                component.add(edge_idx)
                u_1, u_2 = G.edges[edge_idx]["u"], G.edges[edge_idx]["v"]
                if u_1 in G.terminals:    # ターミナルごとに次数を数え、次数2になったらエラー
                    degree[u_1] += 1
                    if degree[u_1] == 2:
                        raise InvalidComponentError()
                if u_2 in G.terminals:
                    degree[u_2] += 1
                    if degree[u_2] == 2:
                        raise InvalidComponentError()                
                w = other_endpoint(G.edges[pathes[w]["pred_edge"]], w)

        def construct_s(X_v):
            if len(X_v) == 2:
                v, w = X_v
                construct_path(v, w)
            else:
                X, v, w = s[X_v]["X"], s[X_v]["v"], s[X_v]["w"]
                construct_path(v, w)
                if w in X:
                    construct_s(X)
                else:
                    construct_s_v(X, w)

        def construct_s_v(X, v):
            X_prime = s_v[X][v]["X_prime"]
            construct_s(add_v(X_prime, v))
            construct_s(add_v(set_dif(X, X_prime), v))

        component = set()
        degree = {v: 0 for v in G.terminals}
        final_X = frozenset(G.terminals)

        try:
            construct_s(final_X)    # DPの情報から最小コストのコンポーネントを復元
        except InvalidComponentError:
            return None    # 次数2のターミナルがあった場合、そこで区切った2つのコンポーネントだけ考えれば十分なので、追加しない
        
        return {
            "cost": s[final_X]["cost"], 
            "component": component
        }

    def Dijkstra_all(self, start):    # startから他の頂点への最短距離をすべて求める
        visited = set()
        result = {v:
                  {
                      "cost": float("inf"),
                      "pred_edge": None
                  }
                  for v in self.vertices}
        result[start]["cost"] = 0

        while True:
            unvisited = {v for v in self.vertices if v not in visited}
            if not unvisited:
                break
            u = min(unvisited, key = lambda v: result[v]["cost"])
            if result[u]["cost"] == float("inf"):
                break
            visited.add(u)
            for e_idx in self.adj[u]:
                edge = self.edges[e_idx]
                v = other_endpoint(edge, u)
                if v in visited:
                    continue
                new_dist = result[u]["cost"] + edge["cost"]
                if new_dist < result[v]["cost"]:
                    result[v]["cost"] = new_dist
                    result[v]["pred_edge"] = e_idx

        return result

class InvalidComponentError(Exception):
    pass

def other_endpoint(edge, v):
    return edge["v"] if edge["u"] == v else edge["u"]

if __name__ == "__main__":
    graph = steiner_graph()
    graph.graph_random(5, 5, 1, 2, 0.1)
    graph.validate()
    graph.graph_plot()
    subset = set()
    for i in range(3):
        subset.add(graph.terminals[i])
    result = graph.Dreyfus_Wagner(subset)
    if result is not None:
        print(result["cost"])
        for i in result["component"]:
            print(graph.edges[i])