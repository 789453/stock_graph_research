import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any

def run_industry_analysis(view_name: str, view_config: dict[str, Any], global_config: dict[str, Any]):
    start_time = time.time()
    print(f"Starting industry analysis for view: {view_name}")
    
    # Find view_key
    view_dirs = list(Path(f"cache/semantic_graph/views/{view_name}").glob("*"))
    if not view_dirs:
        raise FileNotFoundError(f"No results found for {view_name}")
    view_key = view_dirs[0].name
    
    base_cache_path = Path(f"cache/semantic_graph/views/{view_name}/{view_key}")
    layer_path = base_cache_path / "edge_layers"
    baseline_path = base_cache_path / "baselines"
    baseline_path.mkdir(parents=True, exist_ok=True)
    
    # Load edges
    edges = pd.read_parquet(layer_path / "edge_candidates_k100.parquet")
    
    # 1. Edge Score by Rank (T2.1.3)
    score_by_rank = edges.groupby("rank")["score"].agg(["mean", "std", "min", "max"]).reset_index()
    score_by_rank.to_csv(layer_path / "edge_score_by_rank.csv", index=False)
    
    # 2. Mutual Ratio by Rank (T2.1.3)
    mutual_by_rank = edges.groupby("rank")["is_mutual"].mean().reset_index()
    mutual_by_rank.rename(columns={"is_mutual": "mutual_ratio"}, inplace=True)
    mutual_by_rank.to_csv(layer_path / "mutual_ratio_by_rank.csv", index=False)
    
    # 3. Industry Analysis (T2.1.4)
    # Load industry data
    sw_path = global_config["market_data"]["stock_sw_member_path"]
    sw_df = pd.read_parquet(sw_path)
    
    # Get latest industry for each stock
    sw_latest = sw_df.sort_values("in_date").groupby("ts_code").last().reset_index()
    
    # Merge industry info to edges
    edges_with_ind = edges.merge(
        sw_latest[["ts_code", "l1_name", "l2_name", "l3_name"]],
        left_on="src_stock_code",
        right_on="ts_code",
        how="left"
    ).merge(
        sw_latest[["ts_code", "l1_name", "l2_name", "l3_name"]],
        left_on="dst_stock_code",
        right_on="ts_code",
        how="left",
        suffixes=("_src", "_dst")
    )
    
    edges_with_ind["same_l1"] = (edges_with_ind["l1_name_src"] == edges_with_ind["l1_name_dst"]) & edges_with_ind["l1_name_src"].notna()
    edges_with_ind["same_l2"] = (edges_with_ind["l2_name_src"] == edges_with_ind["l2_name_dst"]) & edges_with_ind["l2_name_src"].notna()
    edges_with_ind["same_l3"] = (edges_with_ind["l3_name_src"] == edges_with_ind["l3_name_dst"]) & edges_with_ind["l3_name_src"].notna()
    edges_with_ind["cross_l1"] = (edges_with_ind["l1_name_src"] != edges_with_ind["l1_name_dst"]) & edges_with_ind["l1_name_src"].notna() & edges_with_ind["l1_name_dst"].notna()
    
    # Industry by Rank
    ind_by_rank = edges_with_ind.groupby("rank").agg({
        "same_l1": "mean",
        "same_l2": "mean",
        "same_l3": "mean",
        "cross_l1": "mean"
    }).reset_index()
    
    # Calculate Lift (Same L3 ratio / Random Same L3 ratio)
    # Random Same L3 ratio = sum(industry_size^2) / N^2
    ind_counts = sw_latest["l3_name"].value_counts()
    n_total = len(sw_latest)
    random_same_l3_prob = (ind_counts**2).sum() / (n_total**2)
    ind_by_rank["same_l3_lift"] = ind_by_rank["same_l3"] / random_same_l3_prob
    
    ind_by_rank.to_csv(baseline_path / "industry_by_rank.csv", index=False)
    
    # Cumulative TopK Purity
    topk_metrics = []
    for k_val in [5, 10, 20, 50, 100]:
        mask = edges_with_ind["rank"] <= k_val
        subset = edges_with_ind[mask]
        topk_metrics.append({
            "topK": f"top_{k_val:03d}",
            "same_l1": subset["same_l1"].mean(),
            "same_l2": subset["same_l2"].mean(),
            "same_l3": subset["same_l3"].mean(),
            "same_l3_lift": subset["same_l3"].mean() / random_same_l3_prob,
            "cross_l1": subset["cross_l1"].mean()
        })
    pd.DataFrame(topk_metrics).to_csv(baseline_path / "industry_topk_purity.csv", index=False)
    
    # Exclusive Rank Band Purity
    band_metrics = []
    for band_name in edges_with_ind["rank_band_exclusive"].unique():
        if band_name == "out_of_range": continue
        subset = edges_with_ind[edges_with_ind["rank_band_exclusive"] == band_name]
        band_metrics.append({
            "rank_band": band_name,
            "same_l1": subset["same_l1"].mean(),
            "same_l2": subset["same_l2"].mean(),
            "same_l3": subset["same_l3"].mean(),
            "same_l3_lift": subset["same_l3"].mean() / random_same_l3_prob,
            "cross_l1": subset["cross_l1"].mean()
        })
    pd.DataFrame(band_metrics).to_csv(baseline_path / "industry_band_purity.csv", index=False)
    
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_1",
        "task_id": "T2.1.4",
        "task_name": "multi_view_industry_baselines",
        "view_name": view_name,
        "view_key": view_key,
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "inputs": [str(layer_path / "edge_candidates_k100.parquet"), sw_path],
        "outputs": [
            str(baseline_path / "industry_by_rank.csv"),
            str(baseline_path / "industry_topk_purity.csv")
        ],
        "row_counts": {
            "edges": len(edges),
            "random_same_l3_prob": random_same_l3_prob
        }
    }
    
    with open(base_cache_path / "manifests" / "view_industry_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Industry analysis completed for {view_name}. Same L3 (Top 5): {topk_metrics[0]['same_l3']:.4f}")
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    results = []
    for view_name, view_config in config["views"].items():
        res = run_industry_analysis(view_name, view_config, config)
        results.append(res)
        
    # Multi-view Comparison (T2.1.4 Requirement)
    comparison_data = []
    for r in results:
        # Load the band purity for each view
        view_name = r["view_name"]
        view_key = r["view_key"]
        band_purity = pd.read_csv(Path(f"cache/semantic_graph/views/{view_name}/{view_key}/baselines/industry_band_purity.csv"))
        band_purity["view"] = view_name
        comparison_data.append(band_purity)
    
    comparison_df = pd.concat(comparison_data)
    comparison_df.to_csv("cache/semantic_graph/multi_view/comparisons/industry_view_comparison.csv", index=False)
    
    print("Multi-view industry comparison finished.")

if __name__ == "__main__":
    main()
