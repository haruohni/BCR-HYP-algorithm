from dataclasses import dataclass, field
import json

@dataclass
class SteinerGraph:
    isTerminal: dict[bool] = field(default_factory = dict)
    edges: list[dict] = field(default_factory = list)

    def graph_from_json(self,path):
        with open(path,"r",encoding="utf-8") as f:
            data = json.load(f)
        self.isTerminal = {v["id"]:v["terminal"] for v in data["vertices"]}
        self.edges = data["edges"]