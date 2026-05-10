import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any, List, Dict

def pair_corr_for_edges(matrix: np.ndarray, src: np.ndarray, dst: np.ndarray, min_common: int = 24, block: int = 200000):
    """
    Vectorized calculation of Pearson correlation for pairs of nodes.
    matrix: (N, T)
    src, dst: (E,)
    """
    n_edges = len(src)
    results = np.full(n_edges, np.nan, dtype=np.float32)
    
    for lo in range(0, n_edges, block):
        hi = min(lo + block, n_edges)
        X = matrix[src[lo:hi]]
        Y = matrix[dst[lo:hi]]

        valid = np.isfinite(X) & np.isfinite(Y)
        n = valid.sum(axis=1)

        X0 = np.where(valid, X, 0.0)
        Y0 = np.where(valid, Y, 0.0)

        sx = X0.sum(axis=1)
        sy = Y0.sum(axis=1)
        mx = sx / np.maximum(n, 1)
        my = sy / np.maximum(n, 1)

        Xc = np.where(valid, X - mx[:, None], 0.0)
        Yc = np.where(valid, Y - my[:, None], 0.0)

        cov = (Xc * Yc).sum(axis=1)
        vx = (Xc * Xc).sum(axis=1)
        vy = (Yc * Yc).sum(axis=1)
        
        denom = np.sqrt(np.maximum(vx * vy, 1e-12))
        corr = cov / denom
        
        # Mask where n < min_common
        corr[n < min_common] = np.nan
        results[lo:hi] = corr.astype(np.float32)
        
    return results

def pair_cooccurrence_for_edges(matrix: np.ndarray, src: np.ndarray, dst: np.ndarray, min_common: int = 24, block: int = 200000):
    """
    Vectorized calculation of co-occurrence rate for binary flags.
    matrix: (N, T) with 0/1 values
    """
    n_edges = len(src)
    results = np.full(n_edges, np.nan, dtype=np.float32)
    
    for lo in range(0, n_edges, block):
        hi = min(lo + block, n_edges)
        X = matrix[src[lo:hi]]
        Y = matrix[dst[lo:hi]]

        valid = np.isfinite(X) & np.isfinite(Y)
        n = valid.sum(axis=1)
        
        cooccur = ((X == 1) & (Y == 1) & valid).sum(axis=1)
        rate = cooccur / np.maximum(n, 1)
        
        rate[n < min_common] = np.nan
        results[lo:hi] = rate.astype(np.float32)
        
    return results

def pair_lead_lag_for_edges(matrix: np.ndarray, src: np.ndarray, dst: np.ndarray, lag: int = 1, min_common: int = 24, block: int = 200000):
    """
    src leads dst by 'lag' months: corr(src[t], dst[t+lag])
    """
    n_edges = len(src)
    results = np.full(n_edges, np.nan, dtype=np.float32)
    
    # Slice matrix for lag
    # X (src) will be [0 : T-lag]
    # Y (dst) will be [lag : T]
    X_mat = matrix[:, :-lag]
    Y_mat = matrix[:, lag:]
    
    for lo in range(0, n_edges, block):
        hi = min(lo + block, n_edges)
        X = X_mat[src[lo:hi]]
        Y = Y_mat[dst[lo:hi]]

        valid = np.isfinite(X) & np.isfinite(Y)
        n = valid.sum(axis=1)

        X0 = np.where(valid, X, 0.0)
        Y0 = np.where(valid, Y, 0.0)

        mx = X0.sum(axis=1) / np.maximum(n, 1)
        my = Y0.sum(axis=1) / np.maximum(n, 1)

        Xc = np.where(valid, X - mx[:, None], 0.0)
        Yc = np.where(valid, Y - my[:, None], 0.0)

        cov = (Xc * Yc).sum(axis=1)
        vx = (Xc * Xc).sum(axis=1)
        vy = (Yc * Yc).sum(axis=1)
        
        corr = cov / np.sqrt(np.maximum(vx * vy, 1e-12))
        corr[n < min_common] = np.nan
        results[lo:hi] = corr.astype(np.float32)
        
    return results

def compute_view_metrics(view_name: str, global_config: dict[str, Any]):
    start_time = time.time()
    print(f"Computing market behavior metrics for view: {view_name}")
    
    # 1. Load matrices
    matrix_dir = Path("cache/semantic_graph/phase2_2/market_panel/matrices")
    matrix_names = [
        "monthly_return", "ret_resid_market", "ret_resid_l1", 
        "ret_resid_l3", "ret_resid_full_neutral",
        "volatility", "amount_z", "turnover_z", "extreme_up", "extreme_down"
    ]
    matrices = {name: np.load(matrix_dir / f"{name}.npy") for name in matrix_names}
    
    # 2. Locate view edges
    view_dir_22 = Path(f"cache/semantic_graph/phase2_2/views/{view_name}")
    manifest_files = list(view_dir_22.glob("*/manifests/view_edge_freeze_manifest.json"))
    manifest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    view_key = manifest_files[0].parent.parent.name
    
    edges_path = view_dir_22 / view_key / "edge_layers/edge_candidates_k100_fixed.parquet"
    edges = pd.read_parquet(edges_path)
    
    # 3. Define metrics to compute
    # Format: (column_name, matrix_name, function)
    metric_configs = [
        ("corr_raw_return", "monthly_return", pair_corr_for_edges),
        ("corr_resid_market", "ret_resid_market", pair_corr_for_edges),
        ("corr_resid_l1", "ret_resid_l1", pair_corr_for_edges),
        ("corr_resid_l3", "ret_resid_l3", pair_corr_for_edges),
        ("corr_resid_full_neutral", "ret_resid_full_neutral", pair_corr_for_edges),
        ("corr_volatility", "volatility", pair_corr_for_edges),
        ("corr_amount_z", "amount_z", pair_corr_for_edges),
        ("corr_turnover_z", "turnover_z", pair_corr_for_edges),
        ("cooccur_extreme_up", "extreme_up", pair_cooccurrence_for_edges),
        ("cooccur_extreme_down", "extreme_down", pair_cooccurrence_for_edges),
    ]
    
    # 4. Process Semantic Edges
    print("  Processing semantic edges...")
    src_ids = edges["src_node_id"].values
    dst_ids = edges["dst_node_id"].values
    
    min_common = global_config.get("market_panel", {}).get("min_common_months", 24)
    
    for col, mat_name, func in metric_configs:
        print(f"    Computing {col}...")
        edges[col] = func(matrices[mat_name], src_ids, dst_ids, min_common=min_common)
        
    # Lead-lag
    print("    Computing lead-lag (1m)...")
    edges["src_leads_dst_1m"] = pair_lead_lag_for_edges(matrices["ret_resid_full_neutral"], src_ids, dst_ids, lag=1, min_common=min_common)
    edges["dst_leads_src_1m"] = pair_lead_lag_for_edges(matrices["ret_resid_full_neutral"], dst_ids, src_ids, lag=1, min_common=min_common)
    edges["lead_lag_asymmetry_1m"] = edges["src_leads_dst_1m"] - edges["dst_leads_src_1m"]
    
    # Common months count
    valid = np.isfinite(matrices["monthly_return"][src_ids]) & np.isfinite(matrices["monthly_return"][dst_ids])
    edges["common_months"] = valid.sum(axis=1).astype(np.int16)
    
    # 5. Save semantic metrics
    out_dir = view_dir_22 / view_key / "phase2_2/market_behavior"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    edges.to_parquet(out_dir / "edge_market_metrics.parquet", compression="zstd")
    
    # Summary by layer
    summary_cols = [c for c, _, _ in metric_configs] + ["src_leads_dst_1m", "dst_leads_src_1m", "lead_lag_asymmetry_1m", "common_months"]
    layer_summary = edges.groupby("rank_band_exclusive")[summary_cols].mean().reset_index()
    layer_summary.to_csv(out_dir / "edge_market_metrics_by_layer.csv", index=False)
    
    # 6. Process Random Baselines (only means)
    print("  Processing random baselines...")
    baseline_manifest_path = view_dir_22 / view_key / "manifests/view_random_baselines_manifest.json"
    with open(baseline_manifest_path, "r") as f:
        bl_manifest = json.load(f)
        
    random_results = []
    
    for band, bl_paths in bl_manifest["outputs"].items():
        band_edges = edges[edges["rank_band_exclusive"] == band]
        src_ids_band = band_edges["src_node_id"].values
        
        for b_type, path in bl_paths.items():
            print(f"    Computing metrics for {band} - {b_type}...")
            dst_repeats = np.load(path) # (n_repeats, n_edges_in_band)
            n_repeats = dst_repeats.shape[0]
            
            repeat_means = []
            for r in range(n_repeats):
                dst_ids_r = dst_repeats[r]
                
                # For each baseline repeat, we only care about the mean of full_neutral correlation
                # and maybe a few others to save time.
                corr_full = pair_corr_for_edges(matrices["ret_resid_full_neutral"], src_ids_band, dst_ids_r, min_common=min_common)
                
                repeat_means.append({
                    "repeat": r,
                    "corr_resid_full_neutral_mean": float(np.nanmean(corr_full))
                })
                
            df_repeats = pd.DataFrame(repeat_means)
            random_results.append({
                "rank_band": band,
                "baseline_type": b_type,
                "corr_resid_full_neutral_mean_of_repeats": float(df_repeats["corr_resid_full_neutral_mean"].mean()),
                "corr_resid_full_neutral_std_of_repeats": float(df_repeats["corr_resid_full_neutral_mean"].std())
            })
            
    df_random = pd.DataFrame(random_results)
    df_random.to_csv(out_dir / "random_baseline_market_metrics.csv", index=False)
    
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_2",
        "task_id": "T2.2.6",
        "task_name": "compute_edge_market_metrics",
        "view_name": view_name,
        "view_key": view_key,
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "outputs": [
            str(out_dir / "edge_market_metrics.parquet"),
            str(out_dir / "edge_market_metrics_by_layer.csv"),
            str(out_dir / "random_baseline_market_metrics.csv")
        ],
        "safe_to_continue": True
    }
    
    with open(view_dir_22 / view_key / "manifests/view_market_metrics_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    for view_name in config["views"].keys():
        compute_view_metrics(view_name, config)

if __name__ == "__main__":
    main()
