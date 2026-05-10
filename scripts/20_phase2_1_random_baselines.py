import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any, List, Dict

def get_random_edges(
    src_nodes: np.ndarray, 
    pool_nodes: np.ndarray, 
    n_edges: int, 
    seed: int
) -> pd.DataFrame:
    """Generate random edges from src_nodes to pool_nodes."""
    rng = np.random.default_rng(seed)
    # We need to sample for each src node to maintain src distribution
    src_counts = pd.Series(src_nodes).value_counts()
    
    all_src = []
    all_dst = []
    
    for src, count in src_counts.items():
        # Exclude self from pool
        valid_pool = pool_nodes[pool_nodes != src]
        if len(valid_pool) == 0:
            continue
        
        # Sample with replacement if count > pool size, but ideally without
        replace = count > len(valid_pool)
        dsts = rng.choice(valid_pool, size=min(count, len(valid_pool)), replace=replace)
        
        all_src.extend([src] * len(dsts))
        all_dst.extend(dsts.tolist())
        
    return pd.DataFrame({"src_node_id": all_src, "dst_node_id": all_dst})

def run_random_baselines(view_name: str, global_config: dict[str, Any]):
    start_time = time.time()
    print(f"Starting random baselines for view: {view_name}")
    
    # Find view_key
    view_dirs = list(Path(f"cache/semantic_graph/views/{view_name}").glob("*"))
    if not view_dirs:
        raise FileNotFoundError(f"No results found for {view_name}")
    view_key = view_dirs[0].name
    
    base_cache_path = Path(f"cache/semantic_graph/views/{view_name}/{view_key}")
    layer_path = base_cache_path / "edge_layers"
    baseline_path = base_cache_path / "baselines"
    baseline_path.mkdir(parents=True, exist_ok=True)
    
    # Load edges and profile
    edges = pd.read_parquet(layer_path / "edge_candidates_k100.parquet")
    profile = pd.read_parquet("cache/semantic_graph/multi_view/baselines/node_size_liquidity_profile.parquet")
    
    # Load industry
    sw_path = global_config["market_data"]["stock_sw_member_path"]
    sw_df = pd.read_parquet(sw_path)
    sw_latest = sw_df.sort_values("in_date").groupby("ts_code").last().reset_index()
    
    # Merge all info to nodes
    records = pd.read_parquet(global_config["records"]["records_path"])
    nodes = records[["stock_code", "record_id"]].copy()
    nodes["node_id"] = nodes.index
    nodes = nodes.merge(profile, on="stock_code", how="left")
    nodes = nodes.merge(sw_latest[["ts_code", "l1_name", "l3_name"]], left_on="stock_code", right_on="ts_code", how="left")
    
    seed = global_config["baselines"]["random_seed"]
    baseline_types = global_config["baselines"]["baseline_types"]
    
    results = {}
    
    # We'll analyze each rank band
    bands = edges["rank_band_exclusive"].unique()
    
    comparison_rows = []
    
    for band in bands:
        if band == "out_of_range": continue
        band_edges = edges[edges["rank_band_exclusive"] == band]
        src_nodes = band_edges["src_node_id"].values
        n_edges = len(band_edges)
        
        print(f"  Processing band: {band} ({n_edges} edges)")
        
        band_results = {"band": band, "semantic_count": n_edges}
        
        # Calculate semantic metrics for this band
        # (Actually we already have them from T2.1.4, but let's re-calc for consistency)
        band_edges_merged = band_edges.merge(nodes[["node_id", "l1_name", "l3_name", "total_mv_bucket_10", "turnover_rate_bucket_10"]], left_on="src_node_id", right_on="node_id").merge(
            nodes[["node_id", "l1_name", "l3_name", "total_mv_bucket_10", "turnover_rate_bucket_10"]], left_on="dst_node_id", right_on="node_id", suffixes=("_src", "_dst")
        )
        
        band_results["semantic_same_l3"] = float(band_edges_merged.apply(lambda r: r["l3_name_src"] == r["l3_name_dst"] if pd.notna(r["l3_name_src"]) else False, axis=1).mean())
        
        # For each baseline type
        for b_type in baseline_types:
            rng = np.random.default_rng(seed)
            all_random_src = []
            all_random_dst = []
            
            # For each unique src in this band
            unique_srcs = band_edges["src_node_id"].unique()
            for src in unique_srcs:
                count = (band_edges["src_node_id"] == src).sum()
                src_info = nodes.iloc[src]
                
                # Define pool based on baseline type
                pool_mask = nodes["node_id"] != src
                if b_type == "global_random":
                    pass
                elif b_type == "same_l3_random":
                    pool_mask &= (nodes["l3_name"] == src_info["l3_name"])
                elif b_type == "same_l3_same_size_random":
                    pool_mask &= (nodes["l3_name"] == src_info["l3_name"]) & (nodes["total_mv_bucket_10"] == src_info["total_mv_bucket_10"])
                elif b_type == "same_l3_same_liquidity_random":
                    pool_mask &= (nodes["l3_name"] == src_info["l3_name"]) & (nodes["turnover_rate_bucket_10"] == src_info["turnover_rate_bucket_10"])
                elif b_type == "cross_l1_random":
                    pool_mask &= (nodes["l1_name"] != src_info["l1_name"])
                elif b_type == "cross_l1_same_size_liquidity_random":
                    pool_mask &= (nodes["l1_name"] != src_info["l1_name"]) & (nodes["total_mv_bucket_10"] == src_info["total_mv_bucket_10"]) & (nodes["turnover_rate_bucket_10"] == src_info["turnover_rate_bucket_10"])
                
                pool = nodes[pool_mask]["node_id"].values
                if len(pool) > 0:
                    dsts = rng.choice(pool, size=min(count, len(pool)), replace=(count > len(pool)))
                    all_random_src.extend([src] * len(dsts))
                    all_random_dst.extend(dsts.tolist())
            
            random_edges = pd.DataFrame({"src_node_id": all_random_src, "dst_node_id": all_random_dst})
            # Calculate metrics for random edges
            random_merged = random_edges.merge(nodes[["node_id", "l1_name", "l3_name"]], left_on="src_node_id", right_on="node_id").merge(
                nodes[["node_id", "l1_name", "l3_name"]], left_on="dst_node_id", right_on="node_id", suffixes=("_src", "_dst")
            )
            
            same_l3 = float(random_merged.apply(lambda r: r["l3_name_src"] == r["l3_name_dst"] if pd.notna(r["l3_name_src"]) else False, axis=1).mean())
            band_results[f"random_{b_type}_same_l3"] = same_l3
            
        comparison_rows.append(band_results)
        
    comparison_df = pd.DataFrame(comparison_rows)
    comparison_df.to_parquet(baseline_path / "domain_baseline_comparison.parquet", index=False)
    
    # JSON Summary (T2.1.6 Requirement)
    summary = {
        "view_name": view_name,
        "view_key": view_key,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    }
    
    for band in bands:
        if band == "out_of_range": continue
        band_data = comparison_df[comparison_df["band"] == band].iloc[0]
        
        summary[band] = {
            "semantic": {
                "edge_count": int(band_data["semantic_count"]),
                "same_l3_ratio": float(band_data["semantic_same_l3"])
            }
        }
        
        for b_type in baseline_types:
            summary[band][b_type] = {
                "same_l3_ratio": float(band_data[f"random_{b_type}_same_l3"])
            }
    
    with open(baseline_path / "industry_comparison.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_1",
        "task_id": "T2.1.6",
        "task_name": "domain_and_matched_random_baselines",
        "view_name": view_name,
        "view_key": view_key,
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "inputs": [str(layer_path / "edge_candidates_k100.parquet")],
        "outputs": [
            str(baseline_path / "domain_baseline_comparison.parquet"),
            str(baseline_path / "industry_comparison.json")
        ],
        "row_counts": {
            "bands": len(bands)
        }
    }
    
    with open(base_cache_path / "manifests" / "view_baselines_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Random baselines completed for {view_name}.")
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    for view_name in config["views"].keys():
        run_random_baselines(view_name, config)

if __name__ == "__main__":
    main()
