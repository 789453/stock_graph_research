import os
import pandas as pd
import numpy as np
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint

def generate_random_targets(nodes, n_repeats=1):
    # nodes is the full node profile
    # For each node, pick a random target
    n = len(nodes)
    targets = np.random.choice(nodes["node_id"].values, size=n * n_repeats)
    return targets

def generate_constrained_random_targets(nodes, constraint_col, n_repeats=1):
    # Pick a random target from the same constraint_col value
    targets = np.zeros(len(nodes) * n_repeats, dtype=int)
    node_ids = nodes["node_id"].values
    
    for val, group in nodes.groupby(constraint_col):
        group_ids = group["node_id"].values
        # For each node in the group, pick a random target from the same group
        n_in_group = len(group)
        idx_in_overall = np.where(np.isin(node_ids, group_ids))[0]
        
        for r in range(n_repeats):
            # Sample with replacement
            group_targets = np.random.choice(group_ids, size=n_in_group)
            targets[idx_in_overall + r * len(nodes)] = group_targets
            
    return targets

def main():
    run_id = get_run_id()
    np.random.seed(42) # For reproducibility
    
    # Inputs
    edges_path = f"cache/semantic_graph/{run_id}/phase2_3/edge_metrics/edge_candidates_k100_repaired.parquet"
    nodes_path = f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_feature_profile.parquet"
    
    print("Loading data...")
    edges = pd.read_parquet(edges_path)
    nodes = pd.read_parquet(nodes_path)
    
    # 1. Generate Baselines
    print("Generating random baselines...")
    # Global random
    global_targets = generate_random_targets(nodes)
    
    # Same L3 random
    # Handle NaNs in l3_name
    nodes_l3 = nodes.copy()
    nodes_l3["l3_name"] = nodes_l3["l3_name"].fillna("Unknown")
    l3_targets = generate_constrained_random_targets(nodes_l3, "l3_name")
    
    # Matched random (cap_bucket, pb_bucket, turnover_bucket)
    nodes_matched = nodes.copy()
    nodes_matched["match_key"] = (
        nodes_matched["market_cap_bucket"].astype(str) + "_" + 
        nodes_matched["pb_bucket"].astype(str) + "_" + 
        nodes_matched["turnover_bucket"].astype(str)
    )
    matched_targets = generate_constrained_random_targets(nodes_matched, "match_key")
    
    # 2. Compute Statistics by Rank Band
    print("Computing baseline statistics...")
    # This is a bit complex as we need to compare semantic edges against these random targets.
    # The requirement is to compute statistics like same_l1_ratio, same_l3_ratio, etc.
    
    def get_stats(src_ids, dst_ids):
        # src_ids and dst_ids are arrays of node_id
        src_profile = nodes.iloc[src_ids]
        dst_profile = nodes.iloc[dst_ids]
        
        stats = {
            "same_l1_ratio": (src_profile["l1_code"].values == dst_profile["l1_code"].values).mean(),
            "same_l3_ratio": (src_profile["l3_code"].values == dst_profile["l3_code"].values).mean(),
            "abs_log_total_mv_gap_mean": np.abs(src_profile["log_total_mv"].values - dst_profile["log_total_mv"].values).mean(),
        }
        return stats

    # Semantic stats by rank band
    semantic_stats = []
    for band, group in edges.groupby("exclusive_rank_band"):
        if band == "out_of_range": continue
        stats = get_stats(group["src_node_id"].values, group["dst_node_id"].values)
        stats["rank_band"] = band
        stats["type"] = "semantic"
        semantic_stats.append(stats)
        
    # Baseline stats (overall)
    baseline_stats = []
    for t_ids, name in [(global_targets, "global_random"), 
                        (l3_targets, "same_l3_random"), 
                        (matched_targets, "matched_random")]:
        stats = get_stats(nodes["node_id"].values, t_ids)
        stats["rank_band"] = "overall"
        stats["type"] = name
        baseline_stats.append(stats)
        
    summary_df = pd.DataFrame(semantic_stats + baseline_stats)
    
    # Outputs
    table_05_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/tables/table_05_baseline_residual_summary.csv")
    table_05_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(table_05_path, index=False)
    
    # Manifest
    manifest = create_manifest(
        task_id="t07",
        task_name="baseline_metrics",
        status="success",
        inputs=[
            {"path": edges_path, "fingerprint": get_file_fingerprint(edges_path)},
            {"path": nodes_path, "fingerprint": get_file_fingerprint(nodes_path)}
        ],
        outputs=[
            {"path": str(table_05_path), "fingerprint": get_file_fingerprint(str(table_05_path))}
        ],
        parameters={"random_seed": 42}
    )
    save_manifest(manifest, run_id)
    print("Task 07 completed successfully.")

if __name__ == "__main__":
    main()
