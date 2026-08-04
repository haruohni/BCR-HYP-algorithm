from dataclasses import dataclass, field
import json
import random

@dataclass
class steiner_graph:    #ターミナル付きグラフ
    vertices: list[str] = field(default_factory = list)
    is_terminal: dict[str,bool] = field(default_factory = dict)
    terminals: list[str] = field(default_factory = list)
    edges: list[dict] = field(default_factory = list)

    def graph_from_json(self, path):    #pathにグラフのJSONファイルを渡す
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.vertices = [v["id"] for v in data["vertices"]]
        self.is_terminal = {v["id"]: v["terminal"] for v in data["vertices"]}
        self.terminals = [v["id"] for v in data["vertices"] if v["terminal"] == True]
        self.edges = data["edges"]

    def graph_random(self, num_terminals, num_steiner_vertices, edge_prob = 0.3):    #ターミナル、シュタイナー頂点の個数、密度を渡し、辺コストがランダムな連結グラフを生成する
        self.terminals = ["t" + str(i) for i in range(1, num_terminals + 1)]
        steiner_vertices = ["s" + str(i) for i in range(1, num_steiner_vertices + 1)]
        self.vertices = self.terminals + steiner_vertices
        self.is_terminal = {v: v[0] == "t" for v in self.vertices}
        num_vertices = num_terminals + num_steiner_vertices
        self.edges = []
        connect = self.vertices[:]  #連結性を担保する
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