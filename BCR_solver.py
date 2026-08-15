from steiner_graph import steiner_graph as sg
from scipy.optimize import linprog
import sys

def BCR_solver(graph: sg, root = None):    # steiner_graphとオプションでrootの名前を渡すと、BCRの最適解を返す
    if root is None:
        root = graph.vertices[0]
    if root not in graph.vertices:
        raise ValueError("rootはターミナルから指定してください")
    
    num_arcs = len(graph.arcs)
    terminals_no_root = [v for v in graph.terminals if v != root]
    num_terminals = len(terminals_no_root)
    num_vertices = len(graph.vertices)
    num_vars = (num_terminals + 1) * num_arcs

    c_obj = [a["cost"] for a in graph.arcs]
    c_obj += [0] * (num_arcs * num_terminals)

    def flow_var_idx(idx_terminal, idx_arc):
        return (idx_terminal + 1) * num_arcs + idx_arc

    A_ub = []
    for i in range(num_terminals):
        for j in range(num_arcs):
            constraint = [0] * num_vars
            constraint[flow_var_idx(i, j)] = 1
            constraint[j] = -1
            A_ub.append(constraint)
    b_ub = [0] * (num_terminals * num_arcs)

    def eq_constraint_idx(idx_terminal, idx_vertex):
        return idx_terminal * num_vertices + idx_vertex
    
    A_eq = []
    b_eq = [0] * (num_terminals * num_vertices)
    for i in range(num_terminals):
        for j in range(num_vertices):
            constraint = [0] * num_vars
            for a_idx in graph.arcs_in[graph.vertices[j]]:
                constraint[flow_var_idx(i, a_idx)] = -1
            for a_idx in graph.arcs_out[graph.vertices[j]]:
                constraint[flow_var_idx(i, a_idx)] = 1
            A_eq.append(constraint)
            if graph.vertices[j] == terminals_no_root[i]:
                b_eq[eq_constraint_idx(i,j)] = 1
            if graph.vertices[j] == root:
                b_eq[eq_constraint_idx(i,j)] = -1

    bounds = [(0, None)] * num_vars
    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    if not res.success:
        raise RuntimeError("BCRの求解に失敗しました")

    solution = [res.x[i] for i in range(num_arcs)]
    exist_frac = False
    for i in solution:
        if 1e-6 < i and i < 1-1e-6:
            exist_frac = True
            break

    return {
        "optimal_value": res.fun,
        "z": solution,
        "exist_frac": exist_frac
        }

if __name__ == "__main__":
    graph = sg()
    graph.graph_random(4, 6, 1, 5, 0.2)
    graph.validate()
    graph.graph_plot()
    result = BCR_solver(graph)
    graph.BCR_plot(result["z"])