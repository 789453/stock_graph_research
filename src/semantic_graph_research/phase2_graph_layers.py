import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any
from tqdm import tqdm

def prepare_nodes_index(nodes: pd.DataFrame, n: int) -> pd.DataFrame:
    if "node_id" not in nodes.columns:
        raise ValueError("nodes must contain node_id")

    required_cols = {"node_id", "stock_code"}
    missing = required_cols - set(nodes.columns)
    if missing:
        raise ValueError(f"nodes missing required columns: {missing}")

    nodes_idx = nodes.set_index("node_id", drop=False).sort_index()

    expected = np.arange(n)
    actual = nodes_idx.index.to_numpy()

    if not np.array_equal(actual, expected):
        raise ValueError(
            "nodes index is not exactly node_id 0..n-1; "
            f"actual head={actual[:10].tolist()}, expected head={expected[:10].tolist()}"
        )

    if nodes_idx["stock_code"].isna().any():
        bad = nodes_idx.loc[nodes_idx["stock_code"].isna()].head(10).index.tolist()
        raise ValueError(f"nodes contains missing stock_code, examples node_id={bad}")

    if nodes_idx["stock_code"].duplicated().any():
        dup = nodes_idx.loc[nodes_idx["stock_code"].duplicated(), "stock_code"].head(10).tolist()
        raise ValueError(f"duplicated stock_code in nodes, examples={dup}")

    return nodes_idx


def assign_rank_band_exclusive(rank_array: np.ndarray) -> np.ndarray:
    rank = rank_array.astype(np.int32)
    out = np.full(rank.shape, "rank_out_of_range", dtype=object)

    out[(rank >= 1) & (rank <= 5)] = "rank_001_005"
    out[(rank >= 6) & (rank <= 10)] = "rank_006_010"
    out[(rank >= 11) & (rank <= 20)] = "rank_011_020"
    out[(rank >= 21) & (rank <= 50)] = "rank_021_050"
    out[(rank >= 51) & (rank <= 100)] = "rank_051_100"

    if (out == "rank_out_of_range").any():
        bad = rank[out == "rank_out_of_range"][:10].tolist()
        raise ValueError(f"rank out of configured bands, examples={bad}")

    return out


def add_cumulative_topk_flags(edges: pd.DataFrame) -> None:
    edges["top_001_005"] = edges["rank"] <= 5
    edges["top_001_010"] = edges["rank"] <= 10
    edges["top_001_020"] = edges["rank"] <= 20
    edges["top_001_050"] = edges["rank"] <= 50
    edges["top_001_100"] = edges["rank"] <= 100


def build_edge_candidates_fixed(
    neighbors_k100: np.ndarray,
    scores_k100: np.ndarray,
    nodes: pd.DataFrame,
    near_duplicate_score_threshold: float = 0.999999,
) -> pd.DataFrame:
    if neighbors_k100.shape != scores_k100.shape:
        raise ValueError(
            f"neighbors and scores shape mismatch: "
            f"{neighbors_k100.shape} vs {scores_k100.shape}"
        )

    n, k = neighbors_k100.shape
    if k != 100:
        raise ValueError(f"Phase 2.1 expects k=100, got k={k}")

    nodes_idx = prepare_nodes_index(nodes, n)

    src_node_ids = np.repeat(np.arange(n, dtype=np.int32), k)
    dst_node_ids = neighbors_k100.reshape(-1).astype(np.int32)
    rank_array = np.tile(np.arange(1, k + 1, dtype=np.int32), n)
    score_flat = scores_k100.reshape(-1).astype(np.float32)

    if dst_node_ids.min() < 0 or dst_node_ids.max() >= n:
        raise ValueError(
            f"dst_node_id out of range: min={dst_node_ids.min()}, max={dst_node_ids.max()}, n={n}"
        )

    self_mask = src_node_ids == dst_node_ids
    if self_mask.any():
        bad_idx = np.where(self_mask)[0][:10]
        bad = [
            {
                "row_idx": int(i),
                "src_node_id": int(src_node_ids[i]),
                "dst_node_id": int(dst_node_ids[i]),
                "rank": int(rank_array[i]),
                "score": float(score_flat[i]),
            }
            for i in bad_idx
        ]
        raise ValueError(f"self edges found in kNN candidates, examples={bad}")

    edges = pd.DataFrame({
        "src_node_id": src_node_ids,
        "dst_node_id": dst_node_ids,
        "rank": rank_array,
        "score": score_flat,
    })

    if edges.duplicated(["src_node_id", "dst_node_id"]).any():
        bad = edges.loc[
            edges.duplicated(["src_node_id", "dst_node_id"]),
            ["src_node_id", "dst_node_id", "rank", "score"],
        ].head(10).to_dict("records")
        raise ValueError(f"duplicated edge pairs found, examples={bad}")

    edges["src_stock_code"] = nodes_idx.loc[src_node_ids, "stock_code"].to_numpy()
    edges["dst_stock_code" ] = nodes_idx.loc[dst_node_ids, "stock_code"].to_numpy()

    if "record_id" in nodes_idx.columns:
        edges["src_record_id"] = nodes_idx.loc[src_node_ids, "record_id"].to_numpy()
        edges["dst_record_id"] = nodes_idx.loc[dst_node_ids, "record_id"].to_numpy()
    else:
        edges["src_record_id"] = edges["src_node_id"]
        edges["dst_record_id"] = edges["dst_node_id"]

    same_stock = edges["src_stock_code"].to_numpy() == edges["dst_stock_code"].to_numpy()
    if same_stock.any():
        bad = edges.loc[same_stock, ["src_node_id", "dst_node_id", "src_stock_code", "dst_stock_code"]].head(10)
        raise ValueError(f"self stock_code edges found: {bad.to_dict('records')}")

    same_record = edges["src_record_id"].to_numpy() == edges["dst_record_id"].to_numpy()
    if same_record.any():
        bad = edges.loc[same_record, ["src_node_id", "dst_node_id", "src_record_id", "dst_record_id"]].head(10)
        raise ValueError(f"self record_id edges found: {bad.to_dict('records')}")

    reverse = edges[["src_node_id", "dst_node_id", "rank", "score"]].rename(columns={
        "src_node_id": "dst_node_id",
        "dst_node_id": "src_node_id",
        "rank": "reverse_rank",
        "score": "reverse_score",
    })

    edges = edges.merge(
        reverse,
        on=["src_node_id", "dst_node_id"],
        how="left",
        validate="one_to_one",
    )

    edges["is_mutual"] = edges["reverse_rank"].notna()
    edges["reverse_rank"] = edges["reverse_rank"].fillna(-1).astype(np.int32)
    edges["reverse_score"] = edges["reverse_score"].astype(np.float32)

    edges["score_mean_if_mutual"] = np.where(
        edges["is_mutual"].to_numpy(),
        (edges["score"].to_numpy(dtype=np.float32) + edges["reverse_score"].to_numpy(dtype=np.float32)) / 2.0,
        np.nan,
    ).astype(np.float32)

    top1_scores = np.repeat(scores_k100[:, 0].astype(np.float32), k)
    edges["src_top1_score"] = top1_scores
    edges["src_score_gap_from_top1"] = edges["src_top1_score"] - edges["score"]
    edges["src_score_rank_pct"] = edges["rank"] / k

    edges["rank_band_exclusive"] = assign_rank_band_exclusive(edges["rank"].to_numpy())
    add_cumulative_topk_flags(edges)

    edges["near_duplicate_score_flag"] = edges["score"] >= near_duplicate_score_threshold

    mutual_ratio = float(edges["is_mutual"].mean())
    if not (0.0 < mutual_ratio < 1.0):
        sample = edges.head(20).to_dict("records")
        raise ValueError(
            f"invalid mutual_ratio={mutual_ratio}; expected 0<ratio<1 for current k=100 sanity. "
            f"sample={sample[:2]}"
        )

    reverse_score_nonnull = edges.loc[edges["is_mutual"], "reverse_score"].notna().mean()
    if reverse_score_nonnull < 0.999:
        raise ValueError(f"reverse_score missing for mutual edges: nonnull_ratio={reverse_score_nonnull}")

    if (edges.loc[edges["is_mutual"], "reverse_score"].fillna(0.0) == 0.0).mean() > 0.5:
        raise ValueError("too many mutual edges have reverse_score=0.0; likely reverse lookup bug remains")

    return edges


def build_edge_candidates(
    neighbors_k100: np.ndarray,
    scores_k100: np.ndarray,
    nodes: pd.DataFrame,
    rank_bands: dict | None = None,
) -> pd.DataFrame:
    return build_edge_candidates_fixed(
        neighbors_k100=neighbors_k100,
        scores_k100=scores_k100,
        nodes=nodes,
    )

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