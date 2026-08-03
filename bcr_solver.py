"""
BCR (Bidirected Cut Relaxation) Solver for the Steiner Tree Problem
=====================================================================

BCR の定義（本来の形。指数個の制約を持つ）:

    min   sum_{arc a} c(a) * z_a
    s.t.  z(delta+(S)) >= 1     for all S subseteq (V minus root r), with S ∩ R != empty
          z >= 0

ここで各無向辺 {u,v} (cost c) は2本の有向弧 (u,v),(v,u) （どちらもコスト c) に
分割される（bidirected）。r は根として選んだ terminal。

このままだと制約が指数個あるため、素朴には解けない。しかし max-flow/min-cut
双対性を使うと、次の「コンパクトな」等価LPに書き換えられる：

    「z が BCR で feasible」
      <=>
    「各 terminal t (t != r) について、弧容量 z の下で t から r へ
       1単位のフローを流すことが（独立に）可能」

（証明のスケッチ）
  (=>) z が feasible なら、任意の terminal t に対して t を含み r を含まない
       すべての S で z(delta+(S)) >= 1。これはちょうど「t-r 間の最小カット >= 1」
       なので、max-flow min-cut 定理より t から r への1単位のフローが存在。
  (<=) 各 terminal t について 1単位フローが存在するなら、その t に対する
       min-cut は >=1。任意の S (S∩R != empty, r not in S) について、
       S に含まれる terminal t を一つ取れば、S は「t を含み r を含まない
       カット」の一つなので z(delta+(S)) >= (t-r 間の min cut) >= 1。

よって、terminal ごとに独立な s-t フロー変数 f^t を導入し、
「f^t は t から r への1単位フロー」「f^t_a <= z_a （容量制約）」
を課せば、多項式サイズの厳密に等価な LP になる。
"""

import json
import itertools
from scipy.optimize import linprog
from scipy.sparse import lil_matrix, csr_matrix
import sys


def build_and_solve_bcr(vertices, edges, terminals, root, verbose=True):
    """
    vertices: list of vertex names (str)
    edges: list of (u, v, cost) tuples (undirected edge, cost >= 0)
    terminals: list of terminal vertex names (subset of vertices), must include root
    root: root terminal name

    Returns dict with:
      - status: 'optimal' or otherwise
      - objective: optimal BCR LP value
      - z: dict {(u,v): value} for every directed arc with value > 1e-9
      - z_by_edge: dict {(u,v)-as-given: (z_uv, z_vu)} for each original edge
    """
    assert root in terminals, "root must be a terminal"
    assert root in vertices

    n = len(vertices)
    idx = {v: i for i, v in enumerate(vertices)}

    # Build arc list: each undirected edge -> two directed arcs
    arcs = []  # list of (u_idx, v_idx, cost)
    arc_id = {}
    for (u, v, c) in edges:
        assert c >= 0
        arc_id[(u, v)] = len(arcs)
        arcs.append((idx[u], idx[v], c))
        arc_id[(v, u)] = len(arcs)
        arcs.append((idx[v], idx[u], c))
    A = len(arcs)  # number of arcs

    other_terminals = [t for t in terminals if t != root]
    T = len(other_terminals)

    # Variable layout:
    #   z_0 ... z_{A-1}                      (BCR capacities on arcs)
    #   f^{t_1}_0 ... f^{t_1}_{A-1}           (flow of terminal 1 on arcs)
    #   f^{t_2}_0 ... f^{t_2}_{A-1}
    #   ...
    num_vars = A + T * A

    def z_index(a):
        return a

    def f_index(t_pos, a):
        return A + t_pos * A + a

    # Objective: minimize sum c(a) * z_a  (flow vars have zero cost)
    c_obj = [0.0] * num_vars
    for a, (u, v, cost) in enumerate(arcs):
        c_obj[z_index(a)] = cost

    # --- Inequality constraints: f^t_a - z_a <= 0  for every t, a ---
    n_ineq = T * A
    A_ub = lil_matrix((n_ineq, num_vars))
    b_ub = [0.0] * n_ineq
    row = 0
    for t_pos in range(T):
        for a in range(A):
            A_ub[row, f_index(t_pos, a)] = 1.0
            A_ub[row, z_index(a)] = -1.0
            row += 1

    # --- Equality constraints: flow conservation for each terminal t, each vertex v ---
    # outflow(v) - inflow(v) = b_v ,  b_v = 1 if v==t, -1 if v==root, else 0
    n_eq = T * n
    A_eq = lil_matrix((n_eq, num_vars))
    b_eq = [0.0] * n_eq
    row = 0
    for t_pos, t in enumerate(other_terminals):
        t_idx = idx[t]
        r_idx = idx[root]
        for v in range(n):
            for a, (u_a, v_a, cost) in enumerate(arcs):
                if u_a == v:
                    A_eq[row, f_index(t_pos, a)] += 1.0   # outflow
                if v_a == v:
                    A_eq[row, f_index(t_pos, a)] -= 1.0   # inflow
            if v == t_idx:
                b_eq[row] = 1.0
            elif v == r_idx:
                b_eq[row] = -1.0
            else:
                b_eq[row] = 0.0
            row += 1

    A_ub = csr_matrix(A_ub)
    A_eq = csr_matrix(A_eq)

    bounds = [(0, None)] * num_vars

    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method='highs')

    result = {"status": res.status, "message": res.message}
    if res.status != 0:
        result["objective"] = None
        return result

    result["objective"] = res.fun
    z_values = {}
    for a, (u_a, v_a, cost) in enumerate(arcs):
        val = res.x[z_index(a)]
        if val > 1e-7:
            z_values[(vertices[u_a], vertices[v_a])] = val
    result["z"] = z_values

    z_by_edge = {}
    for (u, v, cost) in edges:
        zuv = res.x[z_index(arc_id[(u, v)])]
        zvu = res.x[z_index(arc_id[(v, u)])]
        z_by_edge[(u, v)] = (round(zuv, 6), round(zvu, 6))
    result["z_by_edge"] = z_by_edge

    return result


def print_result(vertices, edges, terminals, root, result):
    print(f"頂点: {vertices}")
    print(f"terminal: {terminals}  (root = {root})")
    print(f"辺: {edges}")
    print("-" * 60)
    if result["status"] != 0:
        print("LP求解に失敗:", result["message"])
        return
    print(f"BCR最適値 (LP objective) = {result['objective']:.6f}")
    print()
    print("各辺の z 値 (u->v, v->u):")
    any_fractional = False
    for (u, v), (zuv, zvu) in result["z_by_edge"].items():
        marker = ""
        for val in (zuv, zvu):
            if 1e-6 < val < 1 - 1e-6:
                marker = "  <-- 分数値 (fractional)"
                any_fractional = True
        print(f"  {u:>4} -> {v:<4} : z={zuv:.4f}     {v:>4} -> {u:<4} : z={zvu:.4f}{marker}")
    print()
    if any_fractional:
        print("=> この最適解には 0 と 1 の中間の値を取る変数が存在します（フラクショナル）。")
    else:
        print("=> この最適解はすべて整数値です（0/1）。")


def load_from_json(path):
    with open(path) as f:
        data = json.load(f)
    vertices = data["vertices"]
    edges = [tuple(e) for e in data["edges"]]
    terminals = data["terminals"]
    root = data["root"]
    return vertices, edges, terminals, root


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python3 bcr_solver.py <graph.json>")
        sys.exit(1)
    vertices, edges, terminals, root = load_from_json(sys.argv[1])
    result = build_and_solve_bcr(vertices, edges, terminals, root)
    print_result(vertices, edges, terminals, root, result)
