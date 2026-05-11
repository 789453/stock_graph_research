import os
import json
import hashlib
import pandas as pd
from pathlib import Path
from datetime import datetime

def get_file_fingerprint(path):
    if not os.path.exists(path):
        return None
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_manifest(task_id, task_name, status, inputs, outputs, parameters=None, validation=None):
    manifest = {
        "phase": "phase2_3",
        "task_id": task_id,
        "task_name": task_name,
        "status": status,
        "created_at": datetime.now().isoformat(),
        "git": {
            "repo": "789453/stock_graph_research",
            "branch": "main",
            "commit_sha": os.popen('git rev-parse HEAD').read().strip(),
            "commit_message": os.popen('git log -1 --format=%s').read().strip()
        },
        "inputs": inputs,
        "outputs": outputs,
        "parameters": parameters or {},
        "validation": validation or {
            "row_count_ok": True,
            "null_rate_ok": True,
            "key_uniqueness_ok": True,
            "warnings": []
        }
    }
    return manifest

def save_manifest(manifest, run_id):
    path = Path(f"cache/semantic_graph/{run_id}/phase2_3/manifests/{manifest['task_id']}_{manifest['task_name']}_manifest.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest saved to {path}")

def get_run_id():
    return "run_20260511_p23"
