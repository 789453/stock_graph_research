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
        res = faiss.StandardGpuResources()
        index = faiss.index_cpu_to_gpu(res, gpu_device, index)

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

def derive_mutual_edges(directed_edges: pd.DataFrame) -> pd.DataFrame:
    edge_set = set(zip(directed_edges["src_node_id"], directed_edges["dst_node_id"]))

    mutual_rows = []
    for _, row in directed_edges.iterrows():
        u, v = row["src_node_id"], row["dst_node_id"]
        if (v, u) in edge_set:
            rev_row = directed_edges[(directed_edges["src_node_id"] == v) & (directed_edges["dst_node_id"] == u)]
            if len(rev_row) > 0:
                score_uv = row["score"]
                score_vu = rev_row.iloc[0]["score"]
                mutual_rows.append({
                    "u_node_id": u,
                    "v_node_id": v,
                    "score_uv": score_uv,
                    "score_vu": score_vu,
                    "score_mean": (score_uv + score_vu) / 2,
                })

    return pd.DataFrame(mutual_rows)