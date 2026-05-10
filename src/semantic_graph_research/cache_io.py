import json
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any

def make_cache_key(input_fingerprints: dict[str, dict[str, str]], config: dict[str, Any]) -> str:
    fp_str = json.dumps(input_fingerprints, sort_keys=True)
    config_str = json.dumps(config, sort_keys=True)
    combined = fp_str + config_str
    return hashlib.sha256(combined.encode()).hexdigest()[:12]

def write_cache_manifest(cache_dir: Path, manifest: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

def read_cache_manifest(cache_dir: Path) -> dict[str, Any]:
    manifest_path = cache_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_nodes(cache_dir: Path, nodes: pd.DataFrame) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    nodes.to_parquet(cache_dir / "nodes.parquet", index=False)

def save_neighbors(cache_dir: Path, neighbors: "NeighborMatrix") -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        cache_dir / f"neighbors_k{neighbors.k}.npz",
        indices=neighbors.indices,
        scores=neighbors.scores,
    )

def save_edges(cache_dir: Path, edges: pd.DataFrame, prefix: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    edges.to_parquet(cache_dir / f"{prefix}.parquet", index=False)

def load_cached_graph(cache_dir: Path) -> dict[str, Any]:
    manifest = read_cache_manifest(cache_dir)
    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    return {
        "manifest": manifest,
        "nodes": nodes,
    }

def save_semantic_audit(cache_dir: Path, audit: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_dir / "semantic_audit.json", "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

def save_graph_stats(cache_dir: Path, k: int, stats: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_dir / f"graph_stats_k{k}.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def save_layout_pca2(cache_dir: Path, layout: pd.DataFrame) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    layout.to_parquet(cache_dir / "layout_pca2.parquet", index=False)