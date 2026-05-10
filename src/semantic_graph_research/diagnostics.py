import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from collections import Counter
from typing import Any
from tqdm import tqdm

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

def compute_graph_stats(nodes: pd.DataFrame, directed_edges: pd.DataFrame, mutual_edges: pd.DataFrame, show_progress: bool = True) -> dict[str, Any]:
    n_nodes = len(nodes)
    n_directed = len(directed_edges)
    n_mutual = len(mutual_edges)

    in_degrees = directed_edges.groupby("dst_node_id").size().reindex(range(n_nodes), fill_value=0).values
    out_degrees = directed_edges.groupby("src_node_id").size().reindex(range(n_nodes), fill_value=0).values

    reciprocity_ratio = n_mutual / n_directed if n_directed > 0 else 0

    mutual_pairs = set(zip(mutual_edges["u_node_id"], mutual_edges["v_node_id"]))

    uf = UnionFind(n_nodes)
    for u, v in tqdm(mutual_pairs, desc="Building mutual components", disable=not show_progress):
        uf.union(u, v)

    component_map = {}
    for node_id in range(n_nodes):
        root = uf.find(node_id)
        if root not in component_map:
            component_map[root] = 0
        component_map[root] += 1

    component_sizes = list(component_map.values())
    max_component_size = max(component_sizes) if component_sizes else 0
    max_component_ratio = max_component_size / n_nodes if n_nodes > 0 else 0
    n_components = len(component_sizes)

    score_mean = directed_edges["score"].mean()
    score_min = directed_edges["score"].min()
    score_max = directed_edges["score"].max()

    top1_mask = directed_edges["rank"] == 1
    top20_mask = directed_edges["rank"] == 20

    top1_mean = directed_edges.loc[top1_mask, "score"].mean() if top1_mask.any() else 0.0
    top20_mean = directed_edges.loc[top20_mask, "score"].mean() if top20_mask.any() else 0.0

    return {
        "n_nodes": n_nodes,
        "n_directed_edges": n_directed,
        "n_mutual_edges": n_mutual,
        "reciprocity_ratio": float(reciprocity_ratio),
        "max_mutual_component_size": max_component_size,
        "max_mutual_component_ratio": float(max_component_ratio),
        "n_mutual_components": n_components,
        "in_degree_mean": float(np.mean(in_degrees)),
        "in_degree_std": float(np.std(in_degrees)),
        "out_degree_mean": float(np.mean(out_degrees)),
        "out_degree_std": float(np.std(out_degrees)),
        "score_mean": float(score_mean),
        "score_min": float(score_min),
        "score_max": float(score_max),
        "top1_score_mean": float(top1_mean),
        "top20_score_mean": float(top20_mean),
        "top1_top20_score_gap": float(top1_mean - top20_mean),
    }

def compute_industry_diagnostics(nodes: pd.DataFrame, directed_edges: pd.DataFrame, sw_member_current: pd.DataFrame, show_progress: bool = True) -> pd.DataFrame:
    node_with_industry = nodes.merge(
        sw_member_current[["ts_code", "l1_name", "l2_name", "l3_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )

    k20_edges = directed_edges[directed_edges["rank"] <= 20].copy()

    k20_with_industry = k20_edges.merge(
        node_with_industry[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_src"),
    )
    k20_with_industry = k20_with_industry.merge(
        node_with_industry[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_dst"),
    )

    k20_with_industry["same_l1"] = (k20_with_industry["l1_name"] == k20_with_industry["l1_name_dst"]) & k20_with_industry["l1_name"].notna()
    k20_with_industry["same_l2"] = (k20_with_industry["l2_name"] == k20_with_industry["l2_name_dst"]) & k20_with_industry["l2_name"].notna()

    l1_purity = k20_with_industry.groupby("src_node_id")["same_l1"].mean()
    l2_purity = k20_with_industry.groupby("src_node_id")["same_l2"].mean()

    result = pd.DataFrame({
        "node_id": l1_purity.index,
        "l1_purity": l1_purity.values,
        "l2_purity": l2_purity.reindex(l1_purity.index).values,
    })

    return result

def make_neighbor_examples(nodes: pd.DataFrame, directed_edges: pd.DataFrame, sw_member_current: pd.DataFrame, n_examples: int = 12) -> pd.DataFrame:
    k20_edges = directed_edges[directed_edges["rank"] <= 20].copy()

    nodes_with_industry = nodes.merge(
        sw_member_current[["ts_code", "l1_name", "l2_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )

    examples = []
    unique_l1 = nodes_with_industry["l1_name"].dropna().unique()

    for l1 in unique_l1[:min(n_examples, len(unique_l1))]:
        stocks_in_l1 = nodes_with_industry[nodes_with_industry["l1_name"] == l1]
        if len(stocks_in_l1) == 0:
            continue
        sample_stock = stocks_in_l1.iloc[0]
        stock_node_id = sample_stock["node_id"]

        neighbors = k20_edges[k20_edges["src_node_id"] == stock_node_id].head(10)
        neighbors = neighbors.merge(
            nodes_with_industry[["node_id", "stock_code", "stock_name", "l1_name", "l2_name"]],
            left_on="dst_node_id",
            right_on="node_id",
            how="left",
            suffixes=("", "_neighbor"),
        )

        for _, neigh in neighbors.iterrows():
            examples.append({
                "src_stock_code": sample_stock["stock_code"],
                "src_stock_name": sample_stock["stock_name"],
                "src_l1": l1,
                "dst_stock_code": neigh["stock_code"],
                "dst_stock_name": neigh["stock_name"],
                "dst_l1": neigh["l1_name"],
                "rank": neigh["rank"],
                "score": neigh["score"],
            })

    return pd.DataFrame(examples)

def compute_layout_pca2(vectors: np.ndarray, node_ids: list[int]) -> pd.DataFrame:
    pca = PCA(n_components=2)
    coords = pca.fit_transform(vectors)

    return pd.DataFrame({
        "node_id": node_ids,
        "x": coords[:, 0],
        "y": coords[:, 1],
        "layout_method": "pca2_for_visualization_only",
    })