import os
import json
import pandas as pd
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint

def validate_artifact_registry(registry_df, strict=True):
    errors = []
    warnings = []
    
    for _, row in registry_df.iterrows():
        path = row["plot_path"]
        if not os.path.exists(path):
            errors.append(f"Missing plot: {path}")
        
        if " " in os.path.basename(path):
            errors.append(f"Filename contains spaces: {path}")
            
        ext = os.path.splitext(path)[1].lower()
        if ext not in [".png", ".svg"]:
            errors.append(f"Invalid extension {ext}: {path}")
            
    return {"errors": errors, "warnings": warnings, "ok": len(errors) == 0}

def check_manifests(run_id):
    manifest_dir = Path(f"cache/semantic_graph/{run_id}/phase2_3/manifests/")
    manifests = list(manifest_dir.glob("*.json"))
    
    results = []
    for m_path in manifests:
        with open(m_path, "r") as f:
            m = json.load(f)
            # Basic checks
            results.append({
                "task_id": m.get("task_id"),
                "status": m.get("status"),
                "outputs_count": len(m.get("outputs", []))
            })
    return results

def main():
    run_id = get_run_id()
    
    # 1. Check manifests
    manifest_results = check_manifests(run_id)
    
    # 2. Check plots (none yet, so registry will be empty or missing)
    plot_registry_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/tables/table_06_plot_registry.csv")
    if plot_registry_path.exists():
        registry_df = pd.read_csv(plot_registry_path)
        plot_validation = validate_artifact_registry(registry_df)
    else:
        plot_validation = {"errors": [], "warnings": ["Plot registry not found yet"], "ok": True}
    
    # Audit summary
    audit_data = {
        "manifest_checks": manifest_results,
        "plot_validation": plot_validation,
        "consistency_ok": plot_validation["ok"]
    }
    
    audit_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/audits/report_consistency_audit.json")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "w") as f:
        json.dump(audit_data, f, indent=2)
    
    # Manifest
    manifest = create_manifest(
        task_id="t02",
        task_name="validate_consistency",
        status="success",
        inputs=[], # T02 audits the current state of phase 2.3
        outputs=[
            {"path": str(audit_path), "fingerprint": get_file_fingerprint(str(audit_path))}
        ],
        validation={
            "consistency_ok": audit_data["consistency_ok"],
            "errors": plot_validation["errors"],
            "warnings": plot_validation["warnings"]
        }
    )
    save_manifest(manifest, run_id)
    print("Task 02 completed successfully.")

if __name__ == "__main__":
    main()
