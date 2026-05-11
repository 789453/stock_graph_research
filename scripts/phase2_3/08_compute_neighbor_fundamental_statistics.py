import os
import pandas as pd
import numpy as np
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint
from scipy.stats import entropy

def main():
    run_id = get_run_id()
    
    # Inputs
    edges_path = f"cache/semantic_graph/{run_id}/phase2_3/edge_metrics/edge_candidates_k100_repaired.parquet"
    nodes_path = f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_feature_profile.parquet"
    graph_metrics_path = f"cache/semantic_graph/{run_id}/phase2_3/graph_metrics/node_graph_metrics_k100.parquet"
    
    print("Loading data...")
    edges = pd.read_parquet(edges_path)
    nodes = pd.read_parquet(nodes_path)
    metrics = pd.read_parquet(graph_metrics_path)
    
    # Merge metrics to nodes
    nodes = nodes.merge(metrics[["node_id", "bridge_score", "hub_score"]], on="node_id", how="left")
    
    # 1. Edge-level gap columns
    print("Computing edge-level fundamental gaps...")
    # Join source and target profiles to edges
    profile_cols = ["node_id", "log_total_mv", "log_circ_mv", "pe_ttm", "pb", "turnover_rate", "l1_name", "l3_name", "board_group", "bridge_score", "hub_score"]
    src_profile = nodes[profile_cols].add_prefix("src_")
    dst_profile = nodes[profile_cols].add_prefix("dst_")
    
    edges_enriched = edges.merge(src_profile, left_on="src_node_id", right_on="src_node_id", how="left")
    edges_enriched = edges_enriched.merge(dst_profile, left_on="dst_node_id", right_on="dst_node_id", how="left")
    
    edges_enriched["abs_log_total_mv_gap"] = np.abs(edges_enriched["src_log_total_mv"] - edges_enriched["dst_log_total_mv"])
    edges_enriched["abs_pb_gap"] = np.abs(edges_enriched["src_pb"] - edges_enriched["dst_pb"])
    edges_enriched["same_sw_l1"] = edges_enriched["src_l1_name"] == edges_enriched["dst_l1_name"]
    edges_enriched["same_sw_l3"] = edges_enriched["src_l3_name"] == edges_enriched["dst_l3_name"]
    
    edge_gaps_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/edge_metrics/edge_neighbor_fundamental_gaps.parquet")
    edges_enriched.to_parquet(edge_gaps_path)
    
    # 2. Node-level neighborhood columns
    print("Computing node-level neighborhood statistics...")
    neighbor_stats = []
    
    # Group by src_node_id (ego node)
    for src_id, group in edges_enriched.groupby("src_node_id"):
        # Neighbors are dst nodes
        stats = {
            "node_id": src_id,
            "neighbor_total_mv_median": group["dst_log_total_mv"].median(),
            "neighbor_pb_median": group["dst_pb"].median(),
            "neighbor_cross_l1_ratio": (group["src_l1_name"] != group["dst_l1_name"]).mean(),
            "neighbor_l1_entropy": entropy(group["dst_l1_name"].value_counts()) if not group["dst_l1_name"].isna().all() else 0.0
        }
        neighbor_stats.append(stats)
        
    neighbor_summary_df = pd.DataFrame(neighbor_stats)
    
    # Output
    neighbor_summary_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_neighbor_fundamental_summary.parquet")
    neighbor_summary_path.parent.mkdir(parents=True, exist_ok=True)
    neighbor_summary_df.to_parquet(neighbor_summary_path)
    
    # Manifest
    manifest = create_manifest(
        task_id="t08",
        task_name="neighbor_stats",
        status="success",
        inputs=[
            {"path": edges_path, "fingerprint": get_file_fingerprint(edges_path)},
            {"path": nodes_path, "fingerprint": get_file_fingerprint(nodes_path)}
        ],
        outputs=[
            {"path": str(edge_gaps_path), "fingerprint": get_file_fingerprint(str(edge_gaps_path))},
            {"path": str(neighbor_summary_path), "fingerprint": get_file_fingerprint(str(neighbor_summary_path))}
        ]
    )
    save_manifest(manifest, run_id)
    print("Task 08 completed successfully.")

if __name__ == "__main__":
    main()
