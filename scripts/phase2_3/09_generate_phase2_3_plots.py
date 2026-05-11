import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint
import json

def setup_style():
    sns.set_theme(style="whitegrid")
    plt.rcParams["figure.figsize"] = (12, 7)
    plt.rcParams["axes.titlesize"] = 14
    plt.rcParams["axes.labelsize"] = 12

def main():
    run_id = get_run_id()
    setup_style()
    
    # Inputs
    feature_profile_path = f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_feature_profile.parquet"
    edge_gaps_path = f"cache/semantic_graph/{run_id}/phase2_3/edge_metrics/edge_neighbor_fundamental_gaps.parquet"
    graph_metrics_path = f"cache/semantic_graph/{run_id}/phase2_3/graph_metrics/node_graph_metrics_k100.parquet"
    baseline_summary_path = f"cache/semantic_graph/{run_id}/phase2_3/tables/table_05_baseline_residual_summary.csv"
    
    print("Loading data...")
    nodes = pd.read_parquet(feature_profile_path)
    edges_enriched = pd.read_parquet(edge_gaps_path)
    metrics = pd.read_parquet(graph_metrics_path)
    baseline_summary = pd.read_csv(baseline_summary_path)
    
    plot_dir = Path(f"cache/semantic_graph/{run_id}/phase2_3/plots")
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    plot_registry = []

    def register_plot(id, path, title, source, caption):
        plot_registry.append({
            "plot_id": id,
            "plot_path": str(path),
            "plot_title": title,
            "source_table": source,
            "created_at": pd.Timestamp.now().isoformat(),
            "caption": caption,
            "status": "generated"
        })

    # P01: Data coverage by SW L1
    print("Generating P01...")
    p01_path = plot_dir / "data_coverage__node_coverage_by_sw_l1.png"
    l1_counts = nodes["l1_name"].value_counts().sort_values()
    l1_counts.plot(kind="barh")
    plt.title("Node Coverage by SW L1 Industry")
    plt.xlabel("Count")
    plt.tight_layout()
    plt.savefig(p01_path)
    plt.close()
    register_plot("P01", p01_path, "Node Coverage by SW L1", "node_feature_profile", "Horizontal bar chart showing the distribution of semantic nodes across SW L1 industries.")

    # P03: Same L1/L2/L3 ratio by rank
    print("Generating P03...")
    p03_path = plot_dir / "industry__same_l1_l2_l3_ratio_by_rank.png"
    # Group by rank and compute ratios
    rank_stats = edges_enriched.groupby("rank").agg({
        "same_sw_l1": "mean",
        "same_sw_l3": "mean"
    })
    rank_stats.plot()
    plt.title("Industry Purity Decay by Rank")
    plt.xlabel("Rank (1-100)")
    plt.ylabel("Ratio")
    plt.tight_layout()
    plt.savefig(p03_path)
    plt.close()
    register_plot("P03", p03_path, "Industry Purity Decay", "edge_neighbor_fundamental_gaps", "Multi-line chart showing the decay of industry purity from rank 1 to 100.")

    # P06: PB gap by rank band
    print("Generating P06...")
    p06_path = plot_dir / "fundamentals__pb_gap_by_rank_band.png"
    sns.boxplot(data=edges_enriched[edges_enriched["exclusive_rank_band"] != "out_of_range"], 
                x="exclusive_rank_band", y="abs_pb_gap")
    plt.title("Absolute PB Gap by Rank Band")
    plt.yscale("log")
    plt.tight_layout()
    plt.savefig(p06_path)
    plt.close()
    register_plot("P06", p06_path, "PB Gap by Rank Band", "edge_neighbor_fundamental_gaps", "Box plot showing the distribution of absolute PB gaps across exclusive rank bands.")

    # P08: In-degree distribution
    print("Generating P08...")
    p08_path = plot_dir / "graph_structure__in_degree_distribution_k100.png"
    sns.histplot(metrics["in_degree"], bins=50)
    plt.axvline(metrics["in_degree"].quantile(0.95), color='r', linestyle='--', label="p95")
    plt.axvline(metrics["in_degree"].quantile(0.99), color='g', linestyle='--', label="p99")
    plt.title("In-degree Distribution (k=100)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(p08_path)
    plt.close()
    register_plot("P08", p08_path, "In-degree Distribution", "node_graph_metrics_k100", "Histogram showing the distribution of node in-degrees with p95 and p99 thresholds.")

    # Save Plot Registry
    registry_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/tables/table_06_plot_registry.csv")
    pd.DataFrame(plot_registry).to_csv(registry_path, index=False)
    
    # Manifest
    manifest = create_manifest(
        task_id="t09",
        task_name="generate_plots",
        status="success",
        inputs=[
            {"path": feature_profile_path, "fingerprint": get_file_fingerprint(feature_profile_path)},
            {"path": edge_gaps_path, "fingerprint": get_file_fingerprint(edge_gaps_path)}
        ],
        outputs=[
            {"path": str(registry_path), "fingerprint": get_file_fingerprint(str(registry_path))}
        ]
    )
    save_manifest(manifest, run_id)
    print("Task 09 completed successfully.")

if __name__ == "__main__":
    main()
