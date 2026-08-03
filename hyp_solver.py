"""
Hypergraphic LP Relaxation (HYP) Solver for the Steiner Tree Problem
========================================================================

HYP (subtour スタイルの定式化。Goemans-Myung / Chakrabarty-Koenemann-Pritchard
などで使われる標準形):

    min   sum_{K subseteq R, |K|>=2} cost(K) * x_K
    s.t.  sum_K x_K * max(|K ∩ S| - 1, 0)  >=  |S| - 1     for all S subseteq R, |S| >= 2
          x >= 0

ここで:
  - R は terminal 集合
  - K は R の部分集合（"full component" が張る terminal の集合）で、|K|>=2
  - cost(K) は、terminal 集合 K をちょうど連結する最小コストの Steiner木のコスト
    （Steiner 頂点を自由に使ってよい。グラフ全体の中での最小木）

BCR と違い、HYP は「根」の概念を必要としない（無向・対称な定式化）。

この定式化には2つの指数的な要素がある:
  (a) 変数の数: R の部分集合の数 (2^|R| 個程度)
  (b) 各変数の係数 cost(K) の計算: これ自体が NP-困難な Steiner木問題

(b) については、terminal数が少なければ Dreyfus-Wagner の動的計画法
(計算量 O(3^k * n + 2^k * (n+m) log n), k=|R|) で厳密に解ける。
(a) はそのまま 2^k 個の変数・制約を持つ LP として解く。

このため、このスクリプトは terminal 数 |R| が小さい（目安として 12〜14 以下）
インスタンス向けです。大きくなると指数的に遅くなります。
"""

import json
import sys
import heapq
from scipy.optimize import linprog
from scipy.sparse import lil_matrix, csr_matrix

INF = float('inf')


def floyd_warshall(n, edges):
    dist = [[INF] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0.0
    for (u, v, c) in edges:
        if c < dist[u][v]:
            dist[u][v] = c
            dist[v][u] = c
    for k in range(n):
        dk = dist[k]
        for i in range(n):
            dik = dist[i][k]
            if dik == INF:
                continue
            di = dist[i]
            for j in range(n):
                nd = dik + dk[j]
                if nd < di[j]:
                    di[j] = nd
    return dist


def dreyfus_wagner(n, adj, dist, terminal_vertex_indices):
    """
    terminal_vertex_indices: R の各 terminal の頂点インデックス（長さ k のリスト）

    戻り値: dp[mask] = 長さ n のリスト。dp[mask][v] は
            「terminal_vertex_indices の mask に対応する terminal 集合をすべて連結し、
             かつ頂点 v にも到達する」最小コストの木のコスト。
            mask のビット i は terminal_vertex_indices[i] に対応 (popcount(mask)>=1)。
    """
    k = len(terminal_vertex_indices)
    full = 1 << k
    dp = [None] * full

    for i in range(k):
        mask = 1 << i
        t = terminal_vertex_indices[i]
        dp[mask] = list(dist[t])

    masks_by_size = sorted(range(1, full), key=lambda m: bin(m).count("1"))

    for mask in masks_by_size:
        if bin(mask).count("1") == 1:
            arr = list(dp[mask])
        else:
            arr = [INF] * n
            sub = (mask - 1) & mask
            while sub > 0:
                comp = mask ^ sub
                dp_sub = dp[sub]
                dp_comp = dp[comp]
                for v in range(n):
                    s = dp_sub[v] + dp_comp[v]
                    if s < arr[v]:
                        arr[v] = s
                sub = (sub - 1) & mask

        # Dijkstra 型の緩和: 「arr を初期距離とみなし、グラフの辺で緩和する」
        # これにより、部分木の結合点から実際の最適点へ経路をつなげる部分を処理する
        visited = [False] * n
        heap = [(arr[v], v) for v in range(n) if arr[v] < INF]
        heapq.heapify(heap)
        while heap:
            d, u = heapq.heappop(heap)
            if visited[u]:
                continue
            if d > arr[u] + 1e-12:
                continue
            visited[u] = True
            for (v, w) in adj[u]:
                nd = d + w
                if nd < arr[v] - 1e-12:
                    arr[v] = nd
                    heapq.heappush(heap, (nd, v))
        dp[mask] = arr

    return dp


def build_and_solve_hyp(vertices, edges, terminals, verbose=True):
    """
    vertices: 頂点名のリスト
    edges: (u, v, cost) のリスト
    terminals: terminal 名のリスト（root の指定は不要）

    戻り値: dict with status, objective, x (各 terminal 部分集合の x_K 値), costs
    """
    n = len(vertices)
    idx = {v: i for i, v in enumerate(vertices)}
    k = len(terminals)
    if k > 16:
        raise ValueError(f"terminal数が {k} 個あり、この実装では大きすぎます（目安: <=14）。")

    term_indices = [idx[t] for t in terminals]

    adj = [[] for _ in range(n)]
    for (u, v, c) in edges:
        adj[idx[u]].append((idx[v], c))
        adj[idx[v]].append((idx[u], c))

    dist = floyd_warshall(n, [(idx[u], idx[v], c) for (u, v, c) in edges])
    dp = dreyfus_wagner(n, adj, dist, term_indices)

    full = 1 << k
    # cost(K) = min_v dp[mask][v]
    cost_of = {}
    for mask in range(1, full):
        if bin(mask).count("1") < 2:
            continue
        cost_of[mask] = min(dp[mask])

    variables = sorted(cost_of.keys())  # masks with popcount>=2
    var_pos = {m: i for i, m in enumerate(variables)}
    num_vars = len(variables)

    full_R_mask = (1 << k) - 1

    # 正しい制約(FKOS14 の LP (M) の制約(1),(2)から導出):
    #   sum_K x_K max(|K∩S|-1,0) <= |S|-1   for all S subsetneq R (S != R)
    #   sum_K x_K (|K|-1)         = |R|-1   for S = R (等式)
    proper_masks = [m for m in variables if m != full_R_mask]
    n_ub = len(proper_masks)

    A_ub = lil_matrix((n_ub, num_vars))
    b_ub = [0.0] * n_ub
    for row, S in enumerate(proper_masks):
        sizeS = bin(S).count("1")
        for K in variables:
            overlap = bin(K & S).count("1")
            coeff = overlap - 1
            if coeff > 0:
                A_ub[row, var_pos[K]] = coeff
        b_ub[row] = sizeS - 1

    A_eq = lil_matrix((1, num_vars))
    for K in variables:
        A_eq[0, var_pos[K]] = bin(K).count("1") - 1
    b_eq = [k - 1]

    A_ub = csr_matrix(A_ub)
    A_eq = csr_matrix(A_eq)
    c_obj = [cost_of[m] for m in variables]
    bounds = [(0, None)] * num_vars

    res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method='highs')

    result = {"status": res.status, "message": res.message}
    if res.status != 0:
        result["objective"] = None
        return result

    result["objective"] = res.fun
    result["x"] = {}
    for i, m in enumerate(variables):
        val = res.x[i]
        if val > 1e-7:
            names = tuple(terminals[j] for j in range(k) if (m >> j) & 1)
            result["x"][names] = (round(val, 6), round(cost_of[m], 6))
    return result


def print_result(vertices, edges, terminals, result):
    print(f"頂点: {vertices}")
    print(f"terminal (R): {terminals}")
    print(f"辺: {edges}")
    print("-" * 60)
    if result["status"] != 0:
        print("LP求解に失敗:", result["message"])
        return
    print(f"HYP最適値 (LP objective) = {result['objective']:.6f}")
    print()
    print("正の値を取る full component (terminal部分集合) とその x_K, cost(K):")
    any_fractional = False
    for names, (val, cost) in sorted(result["x"].items(), key=lambda kv: -kv[1][0]):
        marker = ""
        if 1e-6 < val < 1 - 1e-6:
            marker = "  <-- 分数値 (fractional)"
            any_fractional = True
        print(f"  K={names}  x_K={val:.4f}  cost(K)={cost:.4f}{marker}")
    print()
    if any_fractional:
        print("=> この最適解には 0 と 1 の中間の値を取る x_K が存在します（フラクショナル）。")
    else:
        print("=> この最適解はすべて整数値です（0/1）。")


def load_from_json(path):
    with open(path) as f:
        data = json.load(f)
    vertices = data["vertices"]
    edges = [tuple(e) for e in data["edges"]]
    terminals = data["terminals"]
    return vertices, edges, terminals


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python3 hyp_solver.py <graph.json>")
        print("  (graph.json は root を含まなくてよい。terminals のみ指定)")
        sys.exit(1)
    vertices, edges, terminals = load_from_json(sys.argv[1])
    result = build_and_solve_hyp(vertices, edges, terminals)
    print_result(vertices, edges, terminals, result)
