from dataclasses import dataclass, field
import json
import random
from collections import deque
import networkx as nx

@dataclass
class steiner_graph:    # ターミナル付きグラフ
    vertices: list[str] = field(default_factory = list)
    is_terminal: dict[str,bool] = field(default_factory = dict)
    terminals: list[str] = field(default_factory = list)
    edges: list[dict] = field(default_factory = list)

    def graph_from_json(self, path):    # pathにグラフのJSONファイルを渡す
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vertices = [v["id"] for v in data["vertices"]]
        self.is_terminal = {v["id"]: v["terminal"] for v in data["vertices"]}
        self.terminals = [v["id"] for v in data["vertices"] if v["terminal"] == True]
        self.edges = data["edges"]

    def graph_random(self, num_terminals, num_steiner_vertices, edge_prob = 0.3):    # ターミナル、シュタイナー頂点の個数、密度を渡し、辺コストがランダムな連結グラフを生成する
        if num_terminals < 2:
            raise ValueError(f"num_terminals は2以上が必要です: {num_terminals}")
        self.terminals = ["t" + str(i) for i in range(1, num_terminals + 1)]
        steiner_vertices = ["s" + str(i) for i in range(1, num_steiner_vertices + 1)]
        self.vertices = self.terminals + steiner_vertices
        self.is_terminal = {v: v[0] == "t" for v in self.vertices}
        num_vertices = num_terminals + num_steiner_vertices
        self.edges = []
        connect = self.vertices[:]  # 連結性を担保する
        random.shuffle(connect)
        existing = set()
        for i in range(1, len(connect)):
            u = connect[i]
            v = random.choice(connect[:i])
            self.edges.append({"u": u, "v": v, "cost": random.uniform(1,10)})
            existing.add(frozenset({u,v}))
        for i in range(num_vertices):   #ランダムに辺コストを与える
            for j in range(i+1,num_vertices):
                if frozenset({self.vertices[i],self.vertices[j]}) in existing:
                    continue
                if random.random() < edge_prob:
                    self.edges.append({"u": self.vertices[i], "v": self.vertices[j], "cost": random.uniform(1,10)})

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
        adj = self.build_adjucency()
        start = self.vertices[0]
        visited = {start}
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
        if len(visited) != len(self.vertices):
            raise ValueError("グラフが非連結です")

    def build_adjucency(self):    # 連結性判定の補助として用いる隣接行列
        adj = {v: [] for v in self.vertices}
        for e in self.edges:
            adj[e["u"]].append(e["v"])
            adj[e["v"]].append(e["u"])
        return adj

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

if __name__ == "__main__":
    graph = steiner_graph()
    graph.graph_random(4,4,0.5)
    graph.validate()
    graph.graph_plot()