from steiner_graph import steiner_graph as sg
from scipy.optimize import linprog
import itertools as itt

def HYP_solver(graph: sg):
    components = {}
    for i in range(2, len(graph.terminals) + 1):
        for C in itt.combinations(graph.terminals, i):
            component = graph.Dreyfus_Wagner(C)
            if component is not None:
                components[C] = component

    num_components = len(components)
    c_obj = [component["cost"] for component in components.values()]

    A_ub = []
    b_ub = []
    for i in range(1, len(graph.terminals)):
        for S in itt.combinations(graph.terminals, i):
            constraint = []
            for C in components.keys():
                constraint.append(max(len([v for v in C if v in S]) - 1, 0))
            A_ub.append(constraint)
            b_ub.append(i - 1)

    constraint = []
    for C in components.keys():
        constraint.append(max(len(C) - 1, 0))
    A_eq = [constraint]
    b_eq = [len(graph.terminals) - 1]

    bounds = [(0, None)] * num_components
    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    if not res.success:
        raise RuntimeError("HYPの求解に失敗しました")

    solution = res.x
    num_frac = 0
    for i in solution:
        if 1e-6 < i and i < 1-1e-6:
            num_frac += 1
    if num_frac == 0:
        print("解は整数値です")
    else:
        print("分数解が存在します")

    return {
        "optimal_value": res.fun, 
        "components": components,
        "x": solution
    }

if __name__ == "__main__":
    graph = sg()
    graph.graph_random(4, 6, 1, 5, 0.2)
    graph.validate()
    graph.graph_plot()
    result = HYP_solver(graph)
    print(f"最適値: {result['optimal_value']}")
    terminal_subsets = list(result["components"])
    for i in range(len(terminal_subsets)):
        if result["x"][i] > 1e-6:
            component = result["components"][terminal_subsets[i]]
            print(f"x: {result['x'][i]}, cost: {component['cost']}, component: {[(graph.edges[idx]['u'], graph.edges[idx]['v']) for idx in component['component']]}")