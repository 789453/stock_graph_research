import os
import pandas as pd
import numpy as np
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint

def assign_rank_band_exclusive(rank):
    if 1 <= rank <= 5: return "rank_001_005"
    if 6 <= rank <= 10: return "rank_006_010"
    if 11 <= rank <= 20: return "rank_011_020"
    if 21 <= rank <= 50: return "rank_021_050"
    if 51 <= rank <= 100: return "rank_051_100"
    return "out_of_range"

def main():
    run_id = get_run_id()
    
    # Inputs
    nodes_path = "cache/semantic_graph/2eebde04e582/nodes.parquet"
    edges_path = "cache/semantic_graph/2eebde04e582/phase2/edge_layers/edge_candidates_k100.parquet"
    
    print("Loading nodes and edges...")
    nodes = pd.read_parquet(nodes_path)
    edges = pd.read_parquet(edges_path)
    
    # 1. Enforce node index
    print("Enforcing node index...")
    if "node_id" not in nodes.columns:
        nodes = nodes.reset_index().rename(columns={"index": "node_id"})
    nodes = nodes.sort_values("node_id")
    n = len(nodes)
    if not np.array_equal(nodes["node_id"].values, np.arange(n)):
        print("Warning: node_id is not 0..n-1. Re-indexing...")
        nodes["node_id"] = np.arange(n)
    
    # 2. Self-edge validation
    print("Validating self-edges...")
    # Join ts_code to edges if not present
    if "src_ts_code" not in edges.columns or "dst_ts_code" not in edges.columns:
        node_map = nodes.set_index("node_id")["stock_code"] # Phase 2 uses stock_code, will map to ts_code in T03
        edges["src_stock_code"] = edges["src_node_id"].map(node_map)
        edges["dst_stock_code"] = edges["dst_node_id"].map(node_map)
    
    self_edges = edges[
        (edges["src_node_id"] == edges["dst_node_id"]) | 
        (edges["src_stock_code"] == edges["dst_stock_code"])
    ]
    
    if not self_edges.empty:
        print(f"Found {len(self_edges)} self-edges. Removing...")
        edges = edges.drop(self_edges.index)
    
    self_edge_audit_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/audits/self_edge_audit.csv")
    self_edge_audit_path.parent.mkdir(parents=True, exist_ok=True)
    self_edges.to_csv(self_edge_audit_path, index=False)
    
    # 3. Reverse-edge logic (self-merge)
    print("Computing mutual edges...")
    # Drop existing mutual/reverse columns to ensure correct re-computation
    cols_to_drop = ["is_mutual", "reverse_rank", "reverse_score", "score_mean_if_mutual", "rank_band"]
    edges = edges.drop(columns=[c for c in cols_to_drop if c in edges.columns])
    
    rev_edges = edges[["src_node_id", "dst_node_id", "rank", "score"]].rename(columns={
        "src_node_id": "dst_node_id",
        "dst_node_id": "src_node_id",
        "rank": "reverse_rank",
        "score": "reverse_score"
    })
    
    edges = edges.merge(rev_edges, on=["src_node_id", "dst_node_id"], how="left")
    edges["is_mutual"] = edges["reverse_score"].notna()
    edges["score_mean_if_mutual"] = np.where(
        edges["is_mutual"],
        (edges["score"] + edges["reverse_score"]) / 2,
        edges["score"]
    )
    
    # 4. Rank-band logic
    print("Assigning rank bands...")
    edges["exclusive_rank_band"] = edges["rank"].apply(assign_rank_band_exclusive)
    edges["top_005"] = edges["rank"] <= 5
    edges["top_010"] = edges["rank"] <= 10
    edges["top_020"] = edges["rank"] <= 20
    edges["top_050"] = edges["rank"] <= 50
    edges["top_100"] = edges["rank"] <= 100
    
    # 5. Near duplicate logic
    print("Auditing near duplicates...")
    near_duplicates = edges[edges["score"] >= 0.999999]
    near_duplicate_audit_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/audits/near_duplicate_edge_audit.csv")
    near_duplicates.to_csv(near_duplicate_audit_path, index=False)
    
    # Outputs
    output_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/edge_metrics/edge_candidates_k100_repaired.parquet")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    edges.to_parquet(output_path)
    
    # Validation summary
    val_summary = {
        "row_count_ok": bool(len(edges) == (len(nodes) * 100) - len(self_edges)),
        "self_edge_count": int(len(self_edges)),
        "mutual_ratio": float(edges["is_mutual"].mean()),
        "rank_range_ok": bool(edges["rank"].min() >= 1 and edges["rank"].max() <= 100),
        "score_finite_ok": bool(np.isfinite(edges["score"]).all())
    }
    
    # Manifest
    manifest = create_manifest(
        task_id="t01",
        task_name="edge_repair",
        status="success",
        inputs=[
            {"path": nodes_path, "fingerprint": get_file_fingerprint(nodes_path)},
            {"path": edges_path, "fingerprint": get_file_fingerprint(edges_path)}
        ],
        outputs=[
            {"path": str(output_path), "fingerprint": get_file_fingerprint(str(output_path))},
            {"path": str(self_edge_audit_path), "fingerprint": get_file_fingerprint(str(self_edge_audit_path))},
            {"path": str(near_duplicate_audit_path), "fingerprint": get_file_fingerprint(str(near_duplicate_audit_path))}
        ],
        validation=val_summary
    )
    save_manifest(manifest, run_id)
    print("Task 01 completed successfully.")

if __name__ == "__main__":
    main()
