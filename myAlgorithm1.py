import sys
from steiner_graph import steiner_graph as sg
import BCR_solver
import HYP_solver

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("JSONファイルを指定してください")
        sys.exit(1)
    graph = sg()
    graph.graph_from_json(sys.argv[1])
    graph.validate()
    graph.graph_plot()