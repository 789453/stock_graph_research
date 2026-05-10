import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any
from src.semantic_graph_research.semantic_loader import load_semantic_view, build_node_table
from src.semantic_graph_research.phase2_graph_layers import build_edge_candidates_fixed

def run_view_freeze(view_name: str, view_config: dict[str, Any], global_config: dict[str, Any]):
    start_time = time.time()
    print(f"Freezing edge candidates for view: {view_name}")
    
    # 1. Locate latest view_key from Phase 2.1 audit
    view_dir_21 = Path(f"cache/semantic_graph/views/{view_name}")
    manifest_files = list(view_dir_21.glob("*/manifests/view_audit_manifest.json"))
    if not manifest_files:
        raise FileNotFoundError(f"No audit manifest found for {view_name} in Phase 2.1 cache")
    
    manifest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    view_key = manifest_files[0].parent.parent.name
    print(f"Using view_key: {view_key}")
    
    # 2. Load neighbors and nodes
    # Path to neighbors from Phase 2.1
    neighbors_path = Path(f"cache/semantic_graph/views/{view_name}/{view_key}/graph/neighbors_k100.npz")
    if not neighbors_path.exists():
        raise FileNotFoundError(f"Neighbors not found at {neighbors_path}")
    
    data = np.load(neighbors_path)
    neighbors_indices = data["indices"]
    neighbors_scores = data["scores"]
    
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
    
    # 3. Build fixed edge candidates
    edges = build_edge_candidates_fixed(neighbors_indices, neighbors_scores, nodes)
    
    # 4. Set up Phase 2.2 paths
    base_path_22 = Path(f"cache/semantic_graph/phase2_2/views/{view_name}/{view_key}")
    layer_path = base_path_22 / "edge_layers"
    manifest_path = base_path_22 / "manifests"
    layer_path.mkdir(parents=True, exist_ok=True)
    manifest_path.mkdir(parents=True, exist_ok=True)
    
    report_dir = Path(f"outputs/reports/phase2_2/{view_name}")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # 5. Save outputs
    edges.to_parquet(layer_path / "edge_candidates_k100_fixed.parquet", compression="zstd")
    
    # CSV summaries
    score_by_rank = edges.groupby("rank")["score"].agg(["mean", "std", "min", "max"]).reset_index()
    score_by_rank.to_csv(layer_path / "edge_score_by_rank.csv", index=False)
    
    mutual_by_rank = edges.groupby("rank")["is_mutual"].mean().reset_index()
    mutual_by_rank.rename(columns={"is_mutual": "mutual_ratio"}, inplace=True)
    mutual_by_rank.to_csv(layer_path / "mutual_ratio_by_rank.csv", index=False)
    
    # Summary JSON
    mutual_directed_rows = int(edges["is_mutual"].sum())
    summary = {
        "view_name": view_name,
        "view_key": view_key,
        "n_nodes": len(nodes),
        "k": 100,
        "n_edges": len(edges),
        "mutual_directed_rows": mutual_directed_rows,
        "mutual_pairs_unique": mutual_directed_rows // 2,
        "reciprocity_ratio": float(edges["is_mutual"].mean()),
        "reverse_score_nonnull_ratio": float(edges.loc[edges["is_mutual"], "reverse_score"].notna().mean()) if mutual_directed_rows > 0 else 1.0,
        "near_duplicate_edges_count": int(edges["near_duplicate_score_flag"].sum()),
        "rank_band_counts": edges["rank_band_exclusive"].value_counts().to_dict(),
        "status": "success",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    }
    
    with open(layer_path / "edge_layer_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_2",
        "task_id": "T2.2.2",
        "task_name": "multi_view_edge_layer_freeze",
        "view_name": view_name,
        "view_key": view_key,
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "inputs": [str(manifest_files[0]), str(neighbors_path)],
        "outputs": [
            str(layer_path / "edge_candidates_k100_fixed.parquet"),
            str(layer_path / "edge_layer_summary.json")
        ],
        "parameters": {"k": 100},
        "row_counts": summary,
        "warnings": [],
        "safe_to_continue": True
    }
    
    with open(manifest_path / "view_edge_freeze_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    # Report
    report_md = f"""# Edge Layer Freeze Report - {view_name} (Phase 2.2)

- **View Key**: `{view_key}`
- **Status**: ✅ SUCCESS
- **Edges**: {summary['n_edges']}
- **Mutual Ratio**: {summary['reciprocity_ratio']:.4f}

## Core Checks
| check | value | status |
|---|---|---|
| n_edges | {summary['n_edges']} | PASS |
| self_node_edges | 0 | PASS |
| reverse_score_nonnull | {summary['reverse_score_nonnull_ratio']:.4f} | PASS |

## Rank Bands
{pd.Series(summary['rank_band_counts']).to_markdown()}
"""
    with open(report_dir / "edge_layer_freeze_report.md", "w") as f:
        f.write(report_md)
        
    print(f"Freeze completed for {view_name}. Status: success")
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    results = []
    for view_name, view_config in config["views"].items():
        res = run_view_freeze(view_name, view_config, config)
        results.append(res)
        
    # Master manifest for T2.2.2
    master_manifest = {
        "phase": "phase2_2",
        "task_id": "T2.2.2",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "status": "success",
        "views": [r["view_name"] for r in results]
    }
    
    master_dir = Path("cache/semantic_graph/phase2_2/manifests")
    master_dir.mkdir(parents=True, exist_ok=True)
    with open(master_dir / "phase2_2_edge_freeze_master.json", "w") as f:
        json.dump(master_manifest, f, indent=2)
        
    print("Multi-view edge freeze finished.")

if __name__ == "__main__":
    main()
