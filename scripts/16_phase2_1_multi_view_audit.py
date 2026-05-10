import os
import json
import hashlib
import time
import numpy as np
import pandas as pd
import yaml
import faiss
from pathlib import Path
from typing import Any
from src.semantic_graph_research.semantic_loader import (
    SemanticBundle, SemanticAudit, AlignmentDiagnostics,
    _compute_file_fingerprint, load_semantic_view, audit_semantic_bundle, diagnose_alignment
)

def generate_view_key(view_name: str, config: dict[str, Any], bundle: SemanticBundle) -> str:
    """Generate a unique key for the view based on its content and configuration."""
    vectors_fp = bundle.input_fingerprints["vectors"]
    meta_fp = bundle.input_fingerprints["meta"]
    
    key_data = {
        "view_name": view_name,
        "vectors_path": vectors_fp["path"],
        "vectors_sha256": vectors_fp["sha256"],
        "meta_sha256": meta_fp["sha256"],
        "row_ids_hash": hashlib.sha256(json.dumps(bundle.row_ids).encode()).hexdigest(),
        "shape": bundle.vectors.shape,
        "config_version": config.get("project", {}).get("version", "phase2_1")
    }
    return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:12]

def check_near_duplicates(vectors: np.ndarray, threshold: float = 0.999999) -> pd.DataFrame:
    """Find pairs of vectors with similarity >= threshold."""
    n, d = vectors.shape
    # L2 normalize for inner product similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms < 1e-10] = 1.0
    norm_vecs = vectors / norms
    
    index = faiss.IndexFlatIP(d)
    index.add(norm_vecs)
    
    # Search for top 2 (self and nearest neighbor)
    scores, indices = index.search(norm_vecs, 2)
    
    duplicates = []
    for i in range(n):
        # indices[i, 0] is usually i itself, but we check indices[i, 1] for the nearest neighbor
        for j in range(1, 2):
            score = scores[i, j]
            neighbor_idx = indices[i, j]
            if score >= threshold and i < neighbor_idx:
                duplicates.append({
                    "src_node_id": i,
                    "dst_node_id": int(neighbor_idx),
                    "score": float(score)
                })
    
    return pd.DataFrame(duplicates)

def run_view_audit(view_name: str, view_config: dict[str, Any], global_config: dict[str, Any]):
    start_time = time.time()
    print(f"Starting audit for view: {view_name}")
    
    # Load bundle
    # Note: load_semantic_view expects a config with "semantic" key
    compat_config = {
        "semantic": {
            "vectors_path": view_config["npy_path"],
            "meta_path": view_config["meta_path"],
            "records_path": global_config["records"]["records_path"],
            "expected_rows": global_config["records"]["expected_rows"],
            "expected_dim": global_config["records"]["expected_dim"],
            "expected_dtype": global_config["records"]["expected_dtype"]
        }
    }
    
    bundle = load_semantic_view(compat_config)
    view_key = generate_view_key(view_name, global_config, bundle)
    print(f"Generated view_key: {view_key}")
    
    # Audit
    audit_res = audit_semantic_bundle(bundle, compat_config)
    diag_res = diagnose_alignment(bundle, compat_config["semantic"]["records_path"])
    
    # Near duplicates
    near_dups = check_near_duplicates(bundle.vectors)
    
    # Paths
    base_cache_path = Path(f"cache/semantic_graph/views/{view_name}/{view_key}")
    audit_path = base_cache_path / "audit"
    manifest_path = base_cache_path / "manifests"
    audit_path.mkdir(parents=True, exist_ok=True)
    manifest_path.mkdir(parents=True, exist_ok=True)
    
    report_dir = Path(f"outputs/reports/phase2_1/{view_name}")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Save results
    with open(audit_path / "semantic_audit.json", "w") as f:
        json.dump(audit_res.__dict__, f, indent=2)
    
    with open(audit_path / "alignment_diagnostics.json", "w") as f:
        json.dump(diag_res.__dict__, f, indent=2)
    
    near_dups.to_csv(audit_path / "near_duplicate_pairs.csv", index=False)
    
    with open(audit_path / "near_duplicate_summary.json", "w") as f:
        json.dump({
            "count": len(near_dups),
            "threshold": 0.999999,
            "max_score": float(near_dups["score"].max()) if not near_dups.empty else 0.0
        }, f, indent=2)
        
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_1",
        "task_id": "T2.1.1",
        "task_name": "multi_view_semantic_audit",
        "view_name": view_name,
        "view_key": view_key,
        "status": "success" if diag_res.all_checks_passed else "failed",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "inputs": [view_config["npy_path"], view_config["meta_path"], global_config["records"]["records_path"]],
        "outputs": [
            str(audit_path / "semantic_audit.json"),
            str(audit_path / "alignment_diagnostics.json"),
            str(audit_path / "near_duplicate_pairs.csv")
        ],
        "parameters": {
            "near_duplicate_threshold": 0.999999
        },
        "row_counts": {
            "vectors": audit_res.rows,
            "near_duplicates": len(near_dups)
        },
        "warnings": [],
        "error": None if diag_res.all_checks_passed else "Alignment checks failed",
        "safe_to_continue": diag_res.all_checks_passed
    }
    
    with open(manifest_path / "view_audit_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    # Report
    report_md = f"""# {view_name} View Audit Report

## 1. Summary
- **View Key**: `{view_key}`
- **Status**: {"✅ SUCCESS" if diag_res.all_checks_passed else "❌ FAILED"}
- **Nodes**: {audit_res.rows}
- **Dimensions**: {audit_res.dim}
- **Dtype**: `{audit_res.dtype}`

## 2. Semantic Audit
- **Non-finite values**: {audit_res.non_finite_count}
- **Zero norm vectors**: {audit_res.zero_norm_count}
- **L2 Norm**: Min={audit_res.l2_min:.4f}, Mean={audit_res.l2_mean:.4f}, Max={audit_res.l2_max:.4f}

## 3. Alignment Diagnostics
- **Row IDs Unique**: {"✅" if diag_res.row_ids_count == diag_res.row_ids_unique_count else "❌"} ({diag_res.row_ids_unique_count}/{diag_res.row_ids_count})
- **Records Record ID Unique**: {"✅" if diag_res.records_count == diag_res.records_record_id_unique_count else "❌"}
- **Stock Code Unique**: {"✅" if diag_res.records_count == diag_res.stock_code_unique_count else "❌"}
- **Row Order Binding**: {"✅ OK" if diag_res.row_order_binding_ok else "❌ FAILED"}
- **All Checks Passed**: {"✅ YES" if diag_res.all_checks_passed else "❌ NO"}

## 4. Near Duplicates
- **Count (score >= 0.999999)**: {len(near_dups)}
- **Max similarity**: {float(near_dups["score"].max()) if not near_dups.empty else 0.0:.8f}

## 5. Metadata
- **View from Meta**: `{bundle.view}`
- **Has as-of/fina**: {"Yes" if "asof_date" in bundle.meta.get("row_ids", []) or "asof_date" in pd.read_parquet(global_config["records"]["records_path"]).columns else "No"}
"""
    with open(report_dir / "view_audit_report.md", "w") as f:
        f.write(report_md)
        
    print(f"Audit completed for {view_name}. Status: {manifest['status']}")
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    results = []
    for view_name, view_config in config["views"].items():
        res = run_view_audit(view_name, view_config, config)
        results.append(res)
        
    # Multi-view manifest
    mv_manifest = {
        "phase": "phase2_1",
        "task_id": "T2.1.1",
        "task_name": "multi_view_audit_summary",
        "status": "success" if all(r["status"] == "success" for r in results) else "failed",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "view_summaries": [
            {
                "view_name": r["view_name"],
                "view_key": r["view_key"],
                "status": r["status"],
                "n_nodes": r["row_counts"]["vectors"],
                "near_duplicates": r["row_counts"]["near_duplicates"]
            } for r in results
        ]
    }
    
    mv_manifest_path = Path("cache/semantic_graph/multi_view/manifests/multi_view_audit_summary.json")
    mv_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mv_manifest_path, "w") as f:
        json.dump(mv_manifest, f, indent=2)
        
    print(f"Multi-view audit finished. Overall status: {mv_manifest['status']}")

if __name__ == "__main__":
    main()
