import os
import json
import pandas as pd
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint

def audit_commit():
    sha = os.popen('git rev-parse HEAD').read().strip()
    msg = os.popen('git log -1 --format=%s').read().strip()
    time = os.popen('git log -1 --format=%ci').read().strip()
    author = os.popen('git log -1 --format=%an').read().strip()
    dirty = os.popen('git status --porcelain').read().strip() != ""
    
    audit = {
        "full_sha": sha,
        "short_sha": sha[:7],
        "commit_message": msg,
        "author": author,
        "commit_time": time,
        "dirty_worktree": dirty
    }
    return audit

def audit_legacy_outputs():
    # Define legacy directories
    legacy_dirs = [
        "cache/semantic_graph/2eebde04e582/phase2/",
        "outputs/reports/"
    ]
    
    validity_matrix = []
    
    # Check some known files from phase 2.2 summary
    checks = [
        {"path": "cache/semantic_graph/2eebde04e582/phase2/edge_layers/edge_candidates_k100.parquet", "type": "edge_candidates", "status": "recompute_required", "reason": "Repair and hardening required in T01"},
        {"path": "outputs/reports/PHASE2_RESEARCH_SUMMARY.md", "type": "report", "status": "appendix_only", "reason": "Historical context for Phase 2"},
    ]
    
    for check in checks:
        exists = os.path.exists(check["path"])
        validity_matrix.append({
            "path": check["path"],
            "exists": exists,
            "type": check["type"],
            "status": check["status"] if exists else "missing",
            "reason": check["reason"] if exists else "File not found"
        })
    
    return pd.DataFrame(validity_matrix)

def main():
    run_id = get_run_id()
    audit_data = audit_commit()
    
    # Save commit audit
    audit_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/audits/latest_commit_audit.json")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "w") as f:
        json.dump(audit_data, f, indent=2)
    
    # Audit legacy outputs
    matrix_df = audit_legacy_outputs()
    matrix_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/audits/legacy_output_validity_matrix.csv")
    matrix_df.to_csv(matrix_path, index=False)
    
    # Create engineering audit report
    report_content = f"""# PHASE2_3_ENGINEERING_AUDIT

## Latest Commit
- SHA: {audit_data['full_sha']}
- Message: {audit_data['commit_message']}
- Author: {audit_data['author']}
- Time: {audit_data['commit_time']}
- Dirty Worktree: {audit_data['dirty_worktree']}

## Legacy Output Validity Matrix
| Path | Status | Reason |
|---|---|---|
"""
    for _, row in matrix_df.iterrows():
        report_content += f"| {row['path']} | {row['status']} | {row['reason']} |\n"
    
    report_path = Path(f"outputs/reports/phase2_3/PHASE2_3_ENGINEERING_AUDIT.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report_content)
    
    # Create manifest
    manifest = create_manifest(
        task_id="t00",
        task_name="input_audit",
        status="success",
        inputs=[],
        outputs=[
            {"path": str(audit_path), "fingerprint": get_file_fingerprint(str(audit_path))},
            {"path": str(matrix_path), "fingerprint": get_file_fingerprint(str(matrix_path))},
            {"path": str(report_path), "fingerprint": get_file_fingerprint(str(report_path))}
        ]
    )
    save_manifest(manifest, run_id)
    print("Task 00 completed successfully.")

if __name__ == "__main__":
    main()
