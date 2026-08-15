from steiner_graph import steiner_graph as sg
from my_algorithm1 import my_algorithm_1
from HYP_solver import HYP_solver

graph = sg()
test_num = 1000
failed_case = 0

for i in range(test_num):
    graph.graph_random(6, 10, 1, 5, 0.2)
    result_HYP = HYP_solver(graph)
    if not result_HYP["exist_frac"]:
        print(f"{i}: 整数解")
        continue
    result_my_algorithm = my_algorithm_1(graph)
    optimized = result_HYP["optimal_value"] == result_my_algorithm["gained_value"]
    print(f"{i}: 分数解, optimized: {optimized}")
    if not optimized:
        failed_case += 1
print(f"failed case: {failed_case}")