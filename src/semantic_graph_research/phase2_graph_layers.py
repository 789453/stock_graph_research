import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any
from tqdm import tqdm

def assign_rank_band(rank: int) -> str:
    if rank <= 5:
        return "core"
    elif rank <= 10:
        return "strong"
    elif rank <= 20:
        return "stable"
    elif rank <= 50:
        return "context"
    else:
        return "extended"

def build_edge_candidates(
    neighbors_k100: np.ndarray,
    scores_k100: np.ndarray,
    nodes: pd.DataFrame,
    rank_bands: dict[str, list[int]]
) -> pd.DataFrame:
    n, k = neighbors_k100.shape

    print("    Building base edge table...")
    src_node_ids = np.repeat(np.arange(n), k)
    dst_node_ids = neighbors_k100.flatten()
    rank_array = np.tile(np.arange(1, k + 1), n)
    score_flat = scores_k100.flatten()
    top1_scores = np.repeat(scores_k100[:, 0], k)
    score_gap_from_top1 = top1_scores - score_flat
    score_rank_pct = rank_array / k

    edges = pd.DataFrame({
        "src_node_id": src_node_ids,
        "dst_node_id": dst_node_ids,
        "src_stock_code": nodes.loc[src_node_ids, "stock_code"].values,
        "dst_stock_code": nodes.loc[dst_node_ids, "stock_code"].values,
        "rank": rank_array,
        "score": score_flat,
        "src_top1_score": top1_scores,
        "src_score_gap_from_top1": score_gap_from_top1,
        "src_score_rank_pct": score_rank_pct,
    })

    print("    Building reverse lookup...")
    reverse_map = {}
    for i in range(len(edges)):
        key = (edges.iloc[i]["dst_node_id"], edges.iloc[i]["src_node_id"])
        if key not in reverse_map:
            reverse_map[key] = edges.iloc[i]["rank"]

    print("    Computing mutual flags (vectorized)...")
    src_dst_pairs = list(zip(edges["dst_node_id"], edges["src_node_id"]))
    is_mutual_arr = np.array([key in reverse_map for key in src_dst_pairs], dtype=bool)
    reverse_rank_arr = np.array([reverse_map.get(key, -1) for key in src_dst_pairs], dtype=np.int32)

    edges["is_mutual"] = is_mutual_arr
    edges["reverse_rank"] = reverse_rank_arr

    print("    Computing reverse scores (vectorized)...")
    score_dict = {i: edges.iloc[i]["score"] for i in range(len(edges))}
    reverse_score_arr = np.array([
        score_dict.get((edges.iloc[i]["dst_node_id"], edges.iloc[i]["src_node_id"]), 0.0)
        for i in tqdm(range(len(edges)), desc="    Reverse score lookup")
    ], dtype=np.float32)
    edges["reverse_score"] = reverse_score_arr

    edges["score_mean_if_mutual"] = np.where(
        edges["is_mutual"],
        (edges["score"] + edges["reverse_score"]) / 2,
        0.0
    )

    print("    Assigning rank bands...")
    edges["rank_band"] = edges["rank"].apply(assign_rank_band)

    print("    Computing score quantiles...")
    score_quantiles = [0.50, 0.70, 0.80, 0.90, 0.95, 0.99]
    global_quantiles = {q: edges["score"].quantile(q) for q in score_quantiles}
    for q, threshold in global_quantiles.items():
        edges[f"score_quantile_{int(q*100)}"] = edges["score"] >= threshold

    return edges

def build_adaptive_core_edges(edges: pd.DataFrame, nodes: pd.DataFrame, min_neighbors: int = 3, max_neighbors: int = 20) -> pd.DataFrame:
    global_p80 = edges["score"].quantile(0.80)

    mutual_mask = edges["is_mutual"] == True
    rank_mask = edges["rank"] <= 20
    score_mask = edges["score"] >= global_p80

    filtered = edges[mutual_mask & rank_mask & score_mask].copy()

    print(f"    adaptive_core: filtered to {len(filtered)} mutual/rank<=20/score>=p80 edges")

    def adaptive_filter(group):
        group = group.sort_values("score", ascending=False)
        if len(group) < min_neighbors:
            return pd.DataFrame()
        local_gap_threshold = np.percentile(group["src_score_gap_from_top1"].values, 75) if len(group) > 1 else 0
        group = group[group["src_score_gap_from_top1"] <= local_gap_threshold]
        return group.head(max_neighbors)

    print("    Applying adaptive rules per node...")
    result = filtered.groupby("src_node_id", group_keys=False).apply(adaptive_filter)
    result = result.reset_index(drop=True)
    print(f"    adaptive_core result: {len(result)} edges")
    return result

def build_adaptive_context_edges(edges: pd.DataFrame, min_neighbors: int = 10, max_neighbors: int = 50) -> pd.DataFrame:
    global_p60 = edges["score"].quantile(0.60)

    rank_mask = edges["rank"] <= 50
    score_mask = edges["score"] >= global_p60

    filtered = edges[rank_mask & score_mask].copy()

    print(f"    adaptive_context: filtered to {len(filtered)} rank<=50/score>=p60 edges")

    def adaptive_filter(group):
        group = group.sort_values("score", ascending=False)
        if len(group) < min_neighbors:
            return pd.DataFrame()
        return group.head(max_neighbors)

    result = filtered.groupby("src_node_id", group_keys=False).apply(adaptive_filter)
    result = result.reset_index(drop=True)
    print(f"    adaptive_context result: {len(result)} edges")
    return result

def build_adaptive_cross_industry_bridge_edges(
    edges: pd.DataFrame,
    nodes: pd.DataFrame,
    sw_member: pd.DataFrame
) -> pd.DataFrame:
    global_p75 = edges["score"].quantile(0.75)

    nodes_with_industry = nodes.merge(
        sw_member[["ts_code", "l1_name", "l3_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )

    edges_merged = edges.merge(
        nodes_with_industry[["node_id", "l1_name", "l3_name"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_src"),
    )
    edges_merged = edges_merged.merge(
        nodes_with_industry[["node_id", "l1_name", "l3_name"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_dst"),
    )

    edges_merged["same_l1"] = (edges_merged["l1_name"] == edges_merged["l1_name_dst"]) & edges_merged["l1_name"].notna()
    edges_merged["cross_industry"] = ~edges_merged["same_l1"]

    cross_mask = edges_merged["cross_industry"] == True
    rank_mask = edges_merged["rank"] <= 100
    score_mask = edges_merged["score"] >= global_p75

    filtered = edges_merged[cross_mask & rank_mask & score_mask].copy()

    print(f"    cross_industry_bridge: filtered to {len(filtered)} cross/rank<=100/score>=p75 edges")

    def cross_filter(group):
        group = group.sort_values(["is_mutual", "score"], ascending=[False, False])
        return group.head(30)

    result = filtered.groupby("src_node_id", group_keys=False).apply(cross_filter)
    result = result.reset_index(drop=True)
    print(f"    cross_industry_bridge result: {len(result)} edges")
    return result

def build_adaptive_within_l3_residual_edges(
    edges: pd.DataFrame,
    nodes: pd.DataFrame,
    sw_member: pd.DataFrame
) -> pd.DataFrame:
    nodes_with_industry = nodes.merge(
        sw_member[["ts_code", "l3_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )

    edges_merged = edges.merge(
        nodes_with_industry[["node_id", "l3_name"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_src"),
    )
    edges_merged = edges_merged.merge(
        nodes_with_industry[["node_id", "l3_name"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_dst"),
    )

    edges_merged["same_l3"] = (edges_merged["l3_name"] == edges_merged["l3_name_dst"]) & edges_merged["l3_name"].notna()

    same_l3_mask = edges_merged["same_l3"] == True
    rank_mask = edges_merged["rank"] <= 50

    filtered = edges_merged[same_l3_mask & rank_mask].copy()

    print(f"    within_l3_residual: filtered to {len(filtered)} same_l3/rank<=50 edges")

    def within_filter(group):
        group = group.sort_values("score", ascending=False)
        return group.head(30)

    result = filtered.groupby("src_node_id", group_keys=False).apply(within_filter)
    result = result.reset_index(drop=True)
    print(f"    within_l3_residual result: {len(result)} edges")
    return result