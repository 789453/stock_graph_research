import numpy as np
import pandas as pd
import faiss
from dataclasses import dataclass
from typing import Any

@dataclass
class NeighborMatrix:
    indices: np.ndarray
    scores: np.ndarray
    k: int

    def __post_init__(self):
        assert self.indices.shape == self.scores.shape
        assert self.indices.dtype == np.int32
        assert self.scores.dtype == np.float32

def build_faiss_knn(vectors: np.ndarray, k: int, gpu_device: int = 0) -> NeighborMatrix:
    n, d = vectors.shape

    vectors_copy = vectors.copy()
    faiss.normalize_L2(vectors_copy)

    index = faiss.IndexFlatIP(d)
    if gpu_device >= 0:
        try:
            res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(res, gpu_device, index)
            print(f"[INFO] Using FAISS GPU device {gpu_device}")
        except Exception as e:
            print(f"[WARN] FAISS GPU initialization failed: {e}. Falling back to CPU.")

    index.add(vectors_copy)

    k_search = k + 1
    all_scores, all_indices = index.search(vectors_copy, k_search)

    final_indices = np.zeros((n, k), dtype=np.int32)
    final_scores = np.zeros((n, k), dtype=np.float32)

    for i in range(n):
        count = 0
        for j in range(k_search):
            if all_indices[i, j] != i:
                final_indices[i, count] = all_indices[i, j]
                final_scores[i, count] = all_scores[i, j]
                count += 1
                if count == k:
                    break
        if count != k:
            raise ValueError(f"row {i} only has {count} non-self neighbors, expected {k}")

    row_ids = np.arange(n, dtype=np.int32)
    has_self = (final_indices == row_ids[:, None]).any()
    if has_self:
        bad_rows = np.where((final_indices == row_ids[:, None]).any(axis=1))[0][:10]
        raise ValueError(f"self-neighbor remains after removal, examples={bad_rows.tolist()}")

    return NeighborMatrix(indices=final_indices, scores=final_scores, k=k)

def neighbors_to_directed_edges(neighbors: NeighborMatrix, node_table: pd.DataFrame) -> pd.DataFrame:
    n = len(node_table)
    k = neighbors.k

    rows = []
    for src_node_id in range(n):
        src_stock_code = node_table.loc[src_node_id, "stock_code"]
        for rank in range(k):
            dst_node_id = neighbors.indices[src_node_id, rank]
            dst_stock_code = node_table.loc[dst_node_id, "stock_code"]
            rows.append({
                "src_node_id": src_node_id,
                "dst_node_id": dst_node_id,
                "src_stock_code": src_stock_code,
                "dst_stock_code": dst_stock_code,
                "rank": rank + 1,
                "score": neighbors.scores[src_node_id, rank],
            })

    return pd.DataFrame(rows)

def derive_mutual_edges_fast(
    directed_edges: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"src_node_id", "dst_node_id", "rank", "score"}
    missing = required - set(directed_edges.columns)
    if missing:
        raise ValueError(f"directed_edges missing columns: {missing}")

    edges = directed_edges.copy()
    edges["src_node_id"] = edges["src_node_id"].astype(np.int32)
    edges["dst_node_id"] = edges["dst_node_id"].astype(np.int32)
    edges["rank"] = edges["rank"].astype(np.int32)
    edges["score"] = edges["score"].astype(np.float32)

    duplicated = edges.duplicated(["src_node_id", "dst_node_id"])
    if duplicated.any():
        bad = edges.loc[duplicated, ["src_node_id", "dst_node_id"]].head(10).to_dict("records")
        raise ValueError(f"duplicated directed edges found, examples={bad}")

    self_edges = edges["src_node_id"].to_numpy() == edges["dst_node_id"].to_numpy()
    if self_edges.any():
        bad = edges.loc[self_edges, ["src_node_id", "dst_node_id", "rank", "score"]].head(10).to_dict("records")
        raise ValueError(f"self edges found in directed_edges, examples={bad}")

    reverse = edges[["src_node_id", "dst_node_id", "rank", "score"]].rename(columns={
        "src_node_id": "dst_node_id",
        "dst_node_id": "src_node_id",
        "rank": "reverse_rank",
        "score": "reverse_score",
    })

    merged = edges.merge(
        reverse,
        on=["src_node_id", "dst_node_id"],
        how="left",
        validate="one_to_one",
    )

    mutual_directed = merged[merged["reverse_rank"].notna()].copy()
    mutual_directed["reverse_rank"] = mutual_directed["reverse_rank"].astype(np.int32)
    mutual_directed["reverse_score"] = mutual_directed["reverse_score"].astype(np.float32)
    mutual_directed["score_mean"] = (
        mutual_directed["score"].astype(np.float32) +
        mutual_directed["reverse_score"].astype(np.float32)
    ) / 2.0

    mutual_directed["u_node_id"] = np.minimum(
        mutual_directed["src_node_id"].to_numpy(),
        mutual_directed["dst_node_id"].to_numpy(),
    )
    mutual_directed["v_node_id"] = np.maximum(
        mutual_directed["src_node_id"].to_numpy(),
        mutual_directed["dst_node_id"].to_numpy(),
    )

    mutual_pairs = (
        mutual_directed
        .sort_values(["u_node_id", "v_node_id", "src_node_id"])
        .drop_duplicates(["u_node_id", "v_node_id"])
        .copy()
    )

    n_directed = len(edges)
    n_mutual_directed = len(mutual_directed)
    n_mutual_pairs = len(mutual_pairs)
    reciprocity_ratio = n_mutual_directed / n_directed if n_directed else 0.0

    if n_mutual_directed != 2 * n_mutual_pairs:
        raise ValueError(
            f"mutual directed rows should equal 2 * unique pairs; "
            f"got {n_mutual_directed=} {n_mutual_pairs=}"
        )

    if not (0.0 <= reciprocity_ratio <= 1.0):
        raise ValueError(f"invalid reciprocity_ratio={reciprocity_ratio}")

    return mutual_directed, mutual_pairs


def derive_mutual_edges(directed_edges: pd.DataFrame) -> pd.DataFrame:
    mutual_directed, _ = derive_mutual_edges_fast(directed_edges)
    return mutual_directed