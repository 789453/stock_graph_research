import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint
from scipy.stats import entropy
import networkx as nx

def compute_metrics_for_k(edges, nodes, k):
    print(f"Computing metrics for k={k}...")
    # Filter edges to top k
    k_edges = edges[edges["rank"] <= k].copy()
    
    # Node list
    node_ids = nodes["node_id"].values
    
    # 1. Degrees
    in_degree = k_edges.groupby("dst_node_id").size().reindex(node_ids, fill_value=0)
    out_degree = k_edges.groupby("src_node_id").size().reindex(node_ids, fill_value=0)
    
    # Weighted degree
    weighted_in_degree = k_edges.groupby("dst_node_id")["score"].sum().reindex(node_ids, fill_value=0.0)
    
    # Mutual degree
    mutual_edges = k_edges[k_edges["is_mutual"] & (k_edges["reverse_rank"] <= k)]
    mutual_in_degree = mutual_edges.groupby("dst_node_id").size().reindex(node_ids, fill_value=0)
    
    # 2. Industry Entropy and Cross-industry
    # Join industry to edges
    l1_map = nodes.set_index("node_id")["l1_name"]
    k_edges["dst_l1"] = k_edges["dst_node_id"].map(l1_map)
    k_edges["src_l1"] = k_edges["src_node_id"].map(l1_map)
    
    # Cross L1
    k_edges["is_cross_l1"] = (k_edges["src_l1"] != k_edges["dst_l1"]) & k_edges["src_l1"].notna() & k_edges["dst_l1"].notna()
    cross_l1_in_degree = k_edges.groupby("dst_node_id")["is_cross_l1"].sum().reindex(node_ids, fill_value=0)
    
    # Entropy per node
    node_entropy = []
    for node_id, group in k_edges.groupby("dst_node_id"):
        l1_counts = group["src_l1"].value_counts()
        node_entropy.append({
            "node_id": node_id,
            "neighbor_l1_entropy": entropy(l1_counts) if not l1_counts.empty else 0.0
        })
    entropy_df = pd.DataFrame(node_entropy).set_index("node_id").reindex(node_ids, fill_value=0.0)
    
    # 3. Bridge and Hub Scores
    # Bridge score = normalized_in_degree * neighbor_l1_entropy * cross_l1_neighbor_ratio * mean_edge_score
    # normalized_in_degree: in_degree / max(in_degree)
    max_in = in_degree.max() if in_degree.max() > 0 else 1
    norm_in = in_degree / max_in
    
    cross_ratio = cross_l1_in_degree / in_degree.replace(0, 1)
    mean_score = k_edges.groupby("dst_node_id")["score"].mean().reindex(node_ids, fill_value=0.0)
    
    bridge_score = norm_in * entropy_df["neighbor_l1_entropy"] * cross_ratio * mean_score
    
    # Hub score = rank_percentile(in_degree) + rank_percentile(weighted_in_degree_sum) + rank_percentile(mutual_in_degree)
    hub_score = (
        in_degree.rank(pct=True) + 
        weighted_in_degree.rank(pct=True) + 
        mutual_in_degree.rank(pct=True)
    )
    
    metrics = pd.DataFrame({
        "node_id": node_ids,
        "in_degree": in_degree.values,
        "out_degree": out_degree.values,
        "mutual_in_degree": mutual_in_degree.values,
        "weighted_in_degree_sum": weighted_in_degree.values,
        "cross_l1_in_degree": cross_l1_in_degree.values,
        "neighbor_l1_entropy": entropy_df["neighbor_l1_entropy"].values,
        "bridge_score": bridge_score.values,
        "hub_score": hub_score.values
    })
    
    # 4. Components (Weakly Connected)
    G = nx.from_pandas_edgelist(k_edges, "src_node_id", "dst_node_id", create_using=nx.DiGraph())
    # Add isolated nodes
    G.add_nodes_from(node_ids)
    
    wcc = list(nx.weakly_connected_components(G))
    scc = list(nx.strongly_connected_components(G))
    
    comp_summary = {
        "k": k,
        "component_count_weak": len(wcc),
        "largest_component_ratio_weak": len(max(wcc, key=len)) / len(node_ids) if wcc else 0,
        "component_count_strong": len(scc),
        "largest_component_ratio_strong": len(max(scc, key=len)) / len(node_ids) if scc else 0
    }
    
    return metrics, comp_summary

def main():
    run_id = get_run_id()
    
    # Inputs
    edges_path = f"cache/semantic_graph/{run_id}/phase2_3/edge_metrics/edge_candidates_k100_repaired.parquet"
    nodes_path = f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_feature_profile.parquet"
    
    print("Loading data...")
    edges = pd.read_parquet(edges_path)
    nodes = pd.read_parquet(nodes_path)
    
    all_comp_summaries = []
    
    for k in [20, 50, 100]:
        metrics, comp_summary = compute_metrics_for_k(edges, nodes, k)
        all_comp_summaries.append(comp_summary)
        
        output_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/graph_metrics/node_graph_metrics_k{k:03d}.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        metrics.to_parquet(output_path)
        
        comp_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/graph_metrics/component_summary_k{k:03d}.json")
        with open(comp_path, "w") as f:
            json.dump(comp_summary, f, indent=2)
            
    # Table 03 summary
    table_03 = pd.DataFrame(all_comp_summaries)
    # Add more columns to table 03 from metrics k=100
    m100_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/graph_metrics/node_graph_metrics_k100.parquet")
    m100 = pd.read_parquet(m100_path)
    
    # Update table_03 with k=100 stats
    # (Simplified for now, can be expanded)
    table_03_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/tables/table_03_graph_metric_summary.csv")
    table_03_path.parent.mkdir(parents=True, exist_ok=True)
    table_03.to_csv(table_03_path, index=False)
    
    # Manifest
    manifest = create_manifest(
        task_id="t06",
        task_name="graph_metrics",
        status="success",
        inputs=[
            {"path": edges_path, "fingerprint": get_file_fingerprint(edges_path)},
            {"path": nodes_path, "fingerprint": get_file_fingerprint(nodes_path)}
        ],
        outputs=[
            {"path": str(table_03_path), "fingerprint": get_file_fingerprint(str(table_03_path))}
        ]
    )
    save_manifest(manifest, run_id)
    print("Task 06 completed successfully.")

if __name__ == "__main__":
    main()
