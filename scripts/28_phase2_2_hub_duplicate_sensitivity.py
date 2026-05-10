import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any, List, Dict

def run_sensitivity_analysis(view_name: str, global_config: dict[str, Any]):
    start_time = time.time()
    print(f"Running sensitivity analysis for view: {view_name}")
    
    # 1. Locate view data
    view_dir_22 = Path(f"cache/semantic_graph/phase2_2/views/{view_name}")
    manifest_files = list(view_dir_22.glob("*/manifests/view_market_metrics_manifest.json"))
    manifest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    view_key = manifest_files[0].parent.parent.name
    
    metrics_dir = view_dir_22 / view_key / "phase2_2/market_behavior"
    edges = pd.read_parquet(metrics_dir / "edge_market_metrics.parquet")
    
    # 2. Identify Hubs
    in_degrees = edges.groupby("dst_node_id").size().sort_values(ascending=False)
    n_nodes = edges["src_node_id"].nunique()
    top_1_percent_threshold = int(n_nodes * 0.01)
    hubs = in_degrees.head(top_1_percent_threshold).index.tolist()
    
    # 3. Sensitivity Sets
    sets = {
        "full": edges,
        "no_near_duplicates": edges[edges["near_duplicate_score_flag"] == False],
        "no_hubs": edges[~edges["dst_node_id"].isin(hubs)],
        "clean": edges[(edges["near_duplicate_score_flag"] == False) & (~edges["dst_node_id"].isin(hubs))]
    }
    
    target_metric = "corr_resid_full_neutral"
    results = []
    
    for set_name, df_subset in sets.items():
        if df_subset.empty: continue
        
        # Calculate overall mean and by rank band
        overall_mean = float(df_subset[target_metric].mean())
        results.append({
            "set_name": set_name,
            "rank_band": "all",
            "n_edges": len(df_subset),
            "mean_corr": overall_mean
        })
        
        for band in ["rank_001_005", "rank_006_010", "rank_011_020"]:
            band_subset = df_subset[df_subset["rank_band_exclusive"] == band]
            if band_subset.empty: continue
            results.append({
                "set_name": set_name,
                "rank_band": band,
                "n_edges": len(band_subset),
                "mean_corr": float(band_subset[target_metric].mean())
            })
            
    df_results = pd.DataFrame(results)
    out_dir = view_dir_22 / view_key / "phase2_2/hub_bridge"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df_results.to_csv(out_dir / "sensitivity_analysis.csv", index=False)
    
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_2",
        "task_id": "T2.2.8",
        "task_name": "hub_duplicate_sensitivity",
        "view_name": view_name,
        "view_key": view_key,
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "outputs": [str(out_dir / "sensitivity_analysis.csv")],
        "safe_to_continue": True
    }
    
    with open(view_dir_22 / view_key / "manifests/view_sensitivity_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    for view_name in config["views"].keys():
        run_sensitivity_analysis(view_name, config)

if __name__ == "__main__":
    main()
