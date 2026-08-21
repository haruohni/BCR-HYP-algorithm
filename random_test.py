from steiner_graph import steiner_graph as sg
from my_algorithm1 import my_algorithm_1
from HYP_solver import HYP_solver
from BCR_solver import BCR_solver

graph = sg()
test_num = 50
failed_case = 0

for i in range(test_num):
    graph.graph_random_bipartite_gadget()
    result_HYP = HYP_solver(graph)
    if not result_HYP["exist_frac"]:
        print(f"{i}: 整数解")
        continue
    result_BCR = BCR_solver(graph)
    result_my_algorithm = my_algorithm_1(graph)
    BCR_HYP_gap = result_HYP["optimal_value"] - result_BCR["optimal_value"] > 1e-6
    optimized = abs(result_HYP["optimal_value"] - result_my_algorithm["gained_value"]) < 1e-6
    print(f"{i}: 分数解, BCR: {result_BCR['optimal_value']}, HYP: {result_HYP['optimal_value']}, BCR-HYP gap: {BCR_HYP_gap}, optimized: {optimized}")
    if not optimized:
        failed_case += 1
        print(f"HYP: {result_HYP["optimal_value"]}, my_algorithm: {result_my_algorithm["gained_value"]}")
print(f"failed case: {failed_case}")