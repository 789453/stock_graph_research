import numpy as np
import pandas as pd
import pytest
from src.semantic_graph_research.graph_builder import derive_mutual_edges_fast
from src.semantic_graph_research.phase2_graph_layers import (
    assign_rank_band_exclusive, 
    build_edge_candidates_fixed,
    prepare_nodes_index
)

def test_derive_mutual_edges_fast_basic():
    # 0 -> 1 (rank 1, score 0.9)
    # 1 -> 0 (rank 2, score 0.8)
    # 0 -> 2 (rank 2, score 0.7)
    # 2 -> 3 (rank 1, score 0.6)
    edges = pd.DataFrame({
        "src_node_id": [0, 1, 0, 2],
        "dst_node_id": [1, 0, 2, 3],
        "rank": [1, 2, 2, 1],
        "score": [0.9, 0.8, 0.7, 0.6],
    })

    mutual_directed, mutual_pairs = derive_mutual_edges_fast(edges)

    assert len(mutual_directed) == 2
    assert len(mutual_pairs) == 1

    # Check u->v
    row_uv = mutual_directed[(mutual_directed["src_node_id"] == 0) & (mutual_directed["dst_node_id"] == 1)].iloc[0]
    assert row_uv["reverse_rank"] == 2
    assert abs(row_uv["reverse_score"] - 0.8) < 1e-6
    assert abs(row_uv["score_mean"] - 0.85) < 1e-6

    # Check v->u
    row_vu = mutual_directed[(mutual_directed["src_node_id"] == 1) & (mutual_directed["dst_node_id"] == 0)].iloc[0]
    assert row_vu["reverse_rank"] == 1
    assert abs(row_vu["reverse_score"] - 0.9) < 1e-6
    assert abs(row_vu["score_mean"] - 0.85) < 1e-6

def test_rank_band_exclusive_naming():
    ranks = np.array([1, 5, 6, 10, 11, 20, 21, 50, 51, 100], dtype=np.int32)
    bands = assign_rank_band_exclusive(ranks).tolist()
    assert bands == [
        "rank_001_005", "rank_001_005",
        "rank_006_010", "rank_006_010",
        "rank_011_020", "rank_011_020",
        "rank_021_050", "rank_021_050",
        "rank_051_100", "rank_051_100"
    ]

def test_prepare_nodes_index_validation():
    nodes = pd.DataFrame({
        "node_id": [0, 1, 2],
        "stock_code": ["A", "B", "C"]
    })
    # Valid
    idx = prepare_nodes_index(nodes, 3)
    assert len(idx) == 3
    
    # Missing node_id
    with pytest.raises(ValueError, match="nodes must contain node_id"):
        prepare_nodes_index(nodes.drop(columns=["node_id"]), 3)
        
    # Duplicate stock_code
    nodes_dup = pd.DataFrame({
        "node_id": [0, 1, 2],
        "stock_code": ["A", "A", "C"]
    })
    with pytest.raises(ValueError, match="duplicated stock_code"):
        prepare_nodes_index(nodes_dup, 3)

def test_build_edge_candidates_fixed_sanity():
    # Need at least 101 nodes to avoid duplicate neighbors with k=100
    n = 150
    k = 100
    nodes = pd.DataFrame({
        "node_id": np.arange(n),
        "stock_code": [f"S{i:03d}" for i in range(n)],
        "record_id": [f"R{i:03d}" for i in range(n)]
    })
    
    # Synthetic neighbors: each node i connects to (i+1)%n, (i+2)%n, ..., (i+k)%n
    neighbors = np.array([[(i + j + 1) % n for j in range(k)] for i in range(n)], dtype=np.int32)
    scores = np.linspace(0.95, 0.5, n * k).reshape(n, k).astype(np.float32)
    
    edges = build_edge_candidates_fixed(neighbors, scores, nodes)
    
    assert len(edges) == n * k
    assert "is_mutual" in edges.columns
    assert "rank_band_exclusive" in edges.columns
    assert "reverse_score" in edges.columns
    
    # Check a mutual edge
    # If 0 -> 1 exists, then 1 -> 0 exists if 1 + j + 1 == 0 (mod 150)
    # 0 -> 1 is rank 1 (j=0)
    # 1 -> 0: 1 + j + 1 = 150 => j = 148. But k=100, so j is in [0, 99].
    # So with this setup, we need smaller k or larger n to ensure some mutuals.
    # Let's force a mutual edge for testing:
    # 0 -> 1 (rank 1)
    # 1 -> 0 (rank 1)
    neighbors[0, 0] = 1
    neighbors[1, 0] = 0
    
    edges = build_edge_candidates_fixed(neighbors, scores, nodes)
    
    row_0_1 = edges[(edges["src_node_id"] == 0) & (edges["dst_node_id"] == 1)].iloc[0]
    assert row_0_1["is_mutual"] == True
    assert row_0_1["reverse_rank"] == 1
    assert abs(row_0_1["reverse_score"] - scores[1, 0]) < 1e-6
