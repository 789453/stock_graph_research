import os
import pandas as pd
import numpy as np
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint

def main():
    run_id = get_run_id()
    
    # Inputs
    feature_profile_path = f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_feature_profile.parquet"
    edge_gaps_path = f"cache/semantic_graph/{run_id}/phase2_3/edge_metrics/edge_neighbor_fundamental_gaps.parquet"
    graph_metric_summary_path = f"cache/semantic_graph/{run_id}/phase2_3/tables/table_03_graph_metric_summary.csv"
    plot_registry_path = f"cache/semantic_graph/{run_id}/phase2_3/tables/table_06_plot_registry.csv"
    baseline_summary_path = f"cache/semantic_graph/{run_id}/phase2_3/tables/table_05_baseline_residual_summary.csv"
    
    print("Loading data...")
    nodes = pd.read_parquet(feature_profile_path)
    edges = pd.read_parquet(edge_gaps_path)
    
    table_dir = Path(f"cache/semantic_graph/{run_id}/phase2_3/tables")
    table_dir.mkdir(parents=True, exist_ok=True)
    
    # Table 02: rank_band_industry_fundamental_summary
    print("Generating Table 02...")
    # Group by exclusive_rank_band
    t02 = edges[edges["exclusive_rank_band"] != "out_of_range"].groupby("exclusive_rank_band").agg({
        "src_node_id": "count",
        "score": ["mean", "median"],
        "is_mutual": "mean",
        "same_sw_l1": "mean",
        "same_sw_l3": "mean",
        "abs_log_total_mv_gap": "mean",
        "abs_pb_gap": "median"
    })
    t02.columns = [
        "edge_count", "score_mean", "score_median", "mutual_ratio",
        "same_l1_ratio", "same_l3_ratio", "abs_log_total_mv_gap_mean", "abs_pb_gap_median"
    ]
    t02 = t02.reset_index().rename(columns={"exclusive_rank_band": "rank_band"})
    t02_path = table_dir / "table_02_rank_band_industry_fundamental_summary.csv"
    t02.to_csv(t02_path, index=False)
    
    # Table 04: cross_industry_bridge_summary
    print("Generating Table 04...")
    # Top cross-L1 industry pairs
    cross_l1 = edges[edges["src_l1_name"] != edges["dst_l1_name"]]
    t04 = cross_l1.groupby(["src_l1_name", "dst_l1_name"]).agg({
        "src_node_id": "count",
        "score": "mean",
        "is_mutual": "mean",
        "src_bridge_score": "mean",
        "abs_pb_gap": "mean"
    }).reset_index()
    t04.columns = ["src_l1_name", "dst_l1_name", "edge_count", "mean_score", "mutual_ratio", "mean_bridge_score", "mean_abs_pb_gap"]
    t04 = t04.sort_values("edge_count", ascending=False).head(20)
    t04_path = table_dir / "table_04_cross_industry_bridge_summary.csv"
    t04.to_csv(t04_path, index=False)
    
    # Manifest
    manifest = create_manifest(
        task_id="t10",
        task_name="generate_tables",
        status="success",
        inputs=[
            {"path": feature_profile_path, "fingerprint": get_file_fingerprint(feature_profile_path)},
            {"path": edge_gaps_path, "fingerprint": get_file_fingerprint(edge_gaps_path)}
        ],
        outputs=[
            {"path": str(t02_path), "fingerprint": get_file_fingerprint(str(t02_path))},
            {"path": str(t04_path), "fingerprint": get_file_fingerprint(str(t04_path))}
        ]
    )
    save_manifest(manifest, run_id)
    print("Task 10 completed successfully.")

if __name__ == "__main__":
    main()
