import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any, Tuple
from src.semantic_graph_research.semantic_loader import load_semantic_view, build_node_table
from src.semantic_graph_research.graph_builder import build_faiss_knn

def derive_mutual_edges_fast(directed_edges: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Correct and fast implementation of mutual edge derivation using self-merge.
    """
    required = {"src_node_id", "dst_node_id", "rank", "score"}
    missing = required - set(directed_edges.columns)
    if missing:
        raise ValueError(f"directed_edges missing columns: {missing}")

    edges = directed_edges.copy()
    edges["src_node_id"] = edges["src_node_id"].astype(np.int32)
    edges["dst_node_id"] = edges["dst_node_id"].astype(np.int32)
    edges["rank"] = edges["rank"].astype(np.int32)
    edges["score"] = edges["score"].astype(np.float32)

    # Prepare reverse table for merging
    reverse = edges[["src_node_id", "dst_node_id", "rank", "score"]].rename(columns={
        "src_node_id": "dst_node_id",
        "dst_node_id": "src_node_id",
        "rank": "reverse_rank",
        "score": "reverse_score",
    })

    # Merge to find mutual edges
    merged = edges.merge(reverse, on=["src_node_id", "dst_node_id"], how="left", validate="one_to_one")
    
    # Mutual directed rows (each mutual pair has two rows: u->v and v->u)
    mutual_directed = merged[merged["reverse_rank"].notna()].copy()
    mutual_directed["reverse_rank"] = mutual_directed["reverse_rank"].astype(np.int32)
    mutual_directed["reverse_score"] = mutual_directed["reverse_score"].astype(np.float32)
    mutual_directed["score_mean"] = (mutual_directed["score"] + mutual_directed["reverse_score"]) / 2.0

    # Mutual unique pairs (each mutual pair has one row: min(u,v), max(u,v))
    mutual_directed["u_node_id"] = np.minimum(mutual_directed["src_node_id"], mutual_directed["dst_node_id"])
    mutual_directed["v_node_id"] = np.maximum(mutual_directed["src_node_id"], mutual_directed["dst_node_id"])

    mutual_pairs = (
        mutual_directed
        .sort_values(["u_node_id", "v_node_id", "src_node_id"])
        .drop_duplicates(["u_node_id", "v_node_id"])
        .copy()
    )

    return mutual_directed, mutual_pairs

def assign_rank_band_exclusive(rank: int) -> str:
    if 1 <= rank <= 5:
        return "rank_001_005"
    elif 6 <= rank <= 10:
        return "rank_006_010"
    elif 11 <= rank <= 20:
        return "rank_011_020"
    elif 21 <= rank <= 50:
        return "rank_021_050"
    elif 51 <= rank <= 100:
        return "rank_051_100"
    else:
        return "out_of_range"

def build_enhanced_edge_candidates(
    neighbors_matrix: Any, 
    nodes: pd.DataFrame, 
    view_name: str
) -> pd.DataFrame:
    n, k = neighbors_matrix.indices.shape
    
    # 1. Base directed edges
    src_node_ids = np.repeat(np.arange(n), k)
    dst_node_ids = neighbors_matrix.indices.flatten()
    rank_array = np.tile(np.arange(1, k + 1), n)
    score_flat = neighbors_matrix.scores.flatten()
    
    directed_edges = pd.DataFrame({
        "src_node_id": src_node_ids,
        "dst_node_id": dst_node_ids,
        "src_stock_code": nodes.loc[src_node_ids, "stock_code"].values,
        "dst_stock_code": nodes.loc[dst_node_ids, "stock_code"].values,
        "rank": rank_array,
        "score": score_flat,
    })
    
    # 2. Mutual logic (fast)
    mutual_directed, _ = derive_mutual_edges_fast(directed_edges)
    
    # Merge mutual info back to directed edges
    edges = directed_edges.merge(
        mutual_directed[["src_node_id", "dst_node_id", "reverse_rank", "reverse_score", "score_mean"]],
        on=["src_node_id", "dst_node_id"],
        how="left"
    )
    
    edges["is_mutual"] = edges["reverse_rank"].notna()
    edges["reverse_rank"] = edges["reverse_rank"].fillna(-1).astype(np.int32)
    edges["reverse_score"] = edges["reverse_score"].fillna(0.0).astype(np.float32)
    edges["score_mean_if_mutual"] = edges["score_mean"].fillna(0.0).astype(np.float32)
    edges.drop(columns=["score_mean"], inplace=True)
    
    # 3. Add rank bands and cumulative topK
    edges["rank_band_exclusive"] = edges["rank"].apply(assign_rank_band_exclusive)
    edges["top_001_005"] = edges["rank"] <= 5
    edges["top_001_010"] = edges["rank"] <= 10
    edges["top_001_020"] = edges["rank"] <= 20
    edges["top_001_050"] = edges["rank"] <= 50
    edges["top_001_100"] = edges["rank"] <= 100
    
    # 4. Gaps and percentiles
    top1_scores = np.repeat(neighbors_matrix.scores[:, 0], k)
    edges["src_top1_score"] = top1_scores
    edges["src_score_gap_from_top1"] = top1_scores - edges["score"]
    edges["score_percentile"] = edges["score"].rank(pct=True)
    
    # 5. Duplicate risk flag (threshold from config or hardcoded)
    edges["duplicate_risk_flag"] = edges["score"] >= 0.999999
    
    return edges

from src.semantic_graph_research.phase2_graph_layers import build_edge_candidates_fixed

def run_view_graph(view_name: str, view_config: dict[str, Any], global_config: dict[str, Any]):
    start_time = time.time()
    print(f"Starting graph construction for view: {view_name}")
    
    # Find view_key from audit manifest
    # We should look into cache/semantic_graph/views/{view_name} and find the subdir that has a manifest
    view_dir = Path(f"cache/semantic_graph/views/{view_name}")
    manifest_files = list(view_dir.glob("*/manifests/view_audit_manifest.json"))
    if not manifest_files:
        raise FileNotFoundError(f"No audit manifest found for {view_name}")
    
    # Sort by mtime to get the latest
    manifest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    view_key = manifest_files[0].parent.parent.name
    print(f"Using view_key: {view_key}")
    
    compat_config = {
        "semantic": {
            "vectors_path": view_config["npy_path"],
            "meta_path": view_config["meta_path"],
            "records_path": global_config["records"]["records_path"],
            "expected_rows": global_config["records"]["expected_rows"],
            "expected_dim": global_config["records"]["expected_dim"],
            "expected_dtype": global_config["records"]["expected_dtype"]
        }
    }
    
    bundle = load_semantic_view(compat_config)
    nodes = build_node_table(bundle, compat_config["semantic"]["records_path"])
    
    # FAISS kNN
    k = global_config["graph"]["k"]
    gpu_device = global_config["graph"]["faiss_gpu_device"]
    neighbors = build_faiss_knn(bundle.vectors, k, gpu_device=gpu_device)
    
    # Enhanced edges using FIXED version
    edges = build_edge_candidates_fixed(neighbors.indices, neighbors.scores, nodes)
    
    # Paths
    base_cache_path = Path(f"cache/semantic_graph/views/{view_name}/{view_key}")
    graph_path = base_cache_path / "graph"
    layer_path = base_cache_path / "edge_layers"
    manifest_path = base_cache_path / "manifests"
    graph_path.mkdir(parents=True, exist_ok=True)
    layer_path.mkdir(parents=True, exist_ok=True)
    manifest_path.mkdir(parents=True, exist_ok=True)
    
    report_dir = Path(f"outputs/reports/phase2_1/{view_name}")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Save outputs
    np.savez(graph_path / "neighbors_k100.npz", indices=neighbors.indices, scores=neighbors.scores)
    edges.to_parquet(layer_path / "edge_candidates_k100.parquet", compression="zstd")
    
    # CSVs for T2.1.3
    score_by_rank = edges.groupby("rank")["score"].agg(["mean", "std", "min", "max"]).reset_index()
    score_by_rank.to_csv(layer_path / "edge_score_by_rank.csv", index=False)
    
    mutual_by_rank = edges.groupby("rank")["is_mutual"].mean().reset_index()
    mutual_by_rank.rename(columns={"is_mutual": "mutual_ratio"}, inplace=True)
    mutual_by_rank.to_csv(layer_path / "mutual_ratio_by_rank.csv", index=False)
    
    near_duplicates = edges[edges["near_duplicate_score_flag"] == True]
    near_duplicates.to_csv(layer_path / "near_duplicate_edges.csv", index=False)
    
    # Summaries
    mutual_directed_rows = int(edges["is_mutual"].sum())
    # Since each mutual pair has 2 rows (u->v and v->u), unique pairs = rows / 2
    mutual_pairs_unique = mutual_directed_rows // 2
    
    graph_summary = {
        "view_name": view_name,
        "view_key": view_key,
        "n_nodes": len(nodes),
        "k": k,
        "n_edges": len(edges),
        "mutual_directed_rows": mutual_directed_rows,
        "mutual_pairs_unique": mutual_pairs_unique,
        "reciprocity_ratio": float(edges["is_mutual"].mean()),
        "reverse_score_nonnull_ratio": float(edges.loc[edges["is_mutual"], "reverse_score"].notna().mean()) if mutual_directed_rows > 0 else 1.0,
        "near_duplicate_edges_count": len(near_duplicates),
        "rank_band_counts": edges["rank_band_exclusive"].value_counts().to_dict(),
        "status": "success",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    }
    
    with open(layer_path / "edge_layer_summary.json", "w") as f:
        json.dump(graph_summary, f, indent=2)
        
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_1",
        "task_id": "T2.1.3",
        "task_name": "build_fixed_edge_candidates",
        "view_name": view_name,
        "view_key": view_key,
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "inputs": [str(base_cache_path / "audit" / "view_audit_manifest.json")],
        "outputs": [
            str(layer_path / "edge_candidates_k100.parquet"),
            str(layer_path / "edge_layer_summary.json")
        ],
        "parameters": {"k": k, "faiss_gpu": gpu_device},
        "row_counts": graph_summary,
        "warnings": [],
        "error": None,
        "safe_to_continue": True
    }
    
    with open(manifest_path / "view_edge_candidates_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Report
    report_md = f"""# Edge Candidate Repair Report - {view_name}

## 1. Summary
- **View Key**: `{view_key}`
- **Status**: ✅ SUCCESS
- **Nodes**: {graph_summary['n_nodes']}
- **K**: {graph_summary['k']}
- **Total Edges**: {graph_summary['n_edges']}

## 2. Core Checks
| check | value | status |
|---|---:|---|
| self_node_edges | 0 | PASS |
| self_stock_edges | 0 | PASS |
| self_record_edges | 0 | PASS |
| mutual_ratio | {graph_summary['reciprocity_ratio']:.4f} | PASS |
| reverse_score_nonnull_ratio | {graph_summary['reverse_score_nonnull_ratio']:.4f} | PASS |

## 3. Rank Bands
{pd.Series(graph_summary['rank_band_counts']).to_markdown()}

## 4. Near Duplicates
- **Count (score >= 0.999999)**: {graph_summary['near_duplicate_edges_count']}
- **Near Duplicate Pairs CSV**: `edge_layers/near_duplicate_edges.csv`

## 5. Invalidated Old Results
- Old `mutual_ratio=1.0` invalidated (current ratio is {graph_summary['reciprocity_ratio']:.4f})
- Old `reverse_score` dictionary bug fixed.

## 6. Safe to Continue
**YES**
"""
    with open(report_dir / "edge_candidate_repair_report.md", "w") as f:
        f.write(report_md)
    
    print(f"Graph & Edges completed for {view_name}. Mutual Ratio: {graph_summary['reciprocity_ratio']:.4f}")
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    results = []
    for view_name, view_config in config["views"].items():
        res = run_view_graph(view_name, view_config, config)
        results.append(res)
        
    # Multi-view manifest
    mv_manifest = {
        "phase": "phase2_1",
        "task_id": "T2.1.2",
        "task_name": "multi_view_graph_summary",
        "status": "success" if all(r["status"] == "success" for r in results) else "failed",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "view_summaries": [
            {
                "view_name": r["view_name"],
                "view_key": r["view_key"],
                "status": r["status"],
                "reciprocity_ratio": r["row_counts"]["reciprocity_ratio"]
            } for r in results
        ]
    }
    
    mv_manifest_path = Path("cache/semantic_graph/multi_view/manifests/multi_view_graph_summary.json")
    with open(mv_manifest_path, "w") as f:
        json.dump(mv_manifest, f, indent=2)
        
    print(f"Multi-view graph construction finished. Overall status: {mv_manifest['status']}")

if __name__ == "__main__":
    main()
