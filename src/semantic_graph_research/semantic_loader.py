import json
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

@dataclass
class SemanticBundle:
    vectors: np.ndarray
    row_ids: list[str]
    view: str
    meta: dict[str, Any]
    input_fingerprints: dict[str, str]

    @property
    def rows(self) -> int:
        return self.vectors.shape[0]

    @property
    def dim(self) -> int:
        return self.vectors.shape[1]

@dataclass
class SemanticAudit:
    rows: int
    dim: int
    dtype: str
    non_finite_count: int
    zero_norm_count: int
    l2_min: float
    l2_mean: float
    l2_max: float
    row_id_unique_count: int
    alignment_ok: bool
    view: str

def _compute_file_fingerprint(path: Path) -> dict[str, str]:
    content = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
        "mtime": str(path.stat().st_mtime),
    }

def load_semantic_view(config: dict[str, Any]) -> SemanticBundle:
    vectors_path = Path(config["semantic"]["vectors_path"])
    meta_path = Path(config["semantic"]["meta_path"])
    records_path = Path(config["semantic"]["records_path"])

    if not vectors_path.exists():
        raise FileNotFoundError(f"NPY file not found: {vectors_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Meta file not found: {meta_path}")
    if not records_path.exists():
        raise FileNotFoundError(f"Records file not found: {records_path}")

    vectors = np.load(vectors_path).astype(np.float32)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    records_df = pd.read_parquet(records_path)
    records_record_ids = set(records_df["record_id"].tolist())

    row_ids = meta["row_ids"]
    vectors_row_ids = set(row_ids)

    missing_in_vectors = records_record_ids - vectors_row_ids
    extra_in_vectors = vectors_row_ids - records_record_ids

    if missing_in_vectors or extra_in_vectors:
        raise ValueError(
            f"Alignment mismatch: {len(missing_in_vectors)} record_ids missing in vectors, "
            f"{len(extra_in_vectors)} extra record_ids in vectors"
        )

    fingerprints = {
        "vectors": _compute_file_fingerprint(vectors_path),
        "meta": _compute_file_fingerprint(meta_path),
        "records": _compute_file_fingerprint(records_path),
    }

    return SemanticBundle(
        vectors=vectors,
        row_ids=row_ids,
        view=meta.get("view", "unknown"),
        meta=meta,
        input_fingerprints=fingerprints,
    )

def audit_semantic_bundle(bundle: SemanticBundle, config: dict[str, Any]) -> SemanticAudit:
    vectors = bundle.vectors
    row_ids = bundle.row_ids

    expected_rows = config["semantic"]["expected_rows"]
    expected_dim = config["semantic"]["expected_dim"]
    expected_dtype = config["semantic"]["expected_dtype"]

    if vectors.ndim != 2:
        raise ValueError(f"Vector shape is {vectors.ndim}D, expected 2D")
    if vectors.shape[0] != expected_rows:
        raise ValueError(f"Vector rows {vectors.shape[0]} != expected {expected_rows}")
    if vectors.shape[1] != expected_dim:
        raise ValueError(f"Vector dim {vectors.shape[1]} != expected {expected_dim}")
    if str(vectors.dtype) != expected_dtype:
        raise ValueError(f"Vector dtype {vectors.dtype} != expected {expected_dtype}")

    non_finite_count = int(np.sum(~np.isfinite(vectors)))
    if non_finite_count > 0:
        raise ValueError(f"Found {non_finite_count} non-finite values in vectors")

    norms = np.linalg.norm(vectors, axis=1)
    zero_norm_count = int(np.sum(norms < 1e-6))

    l2_norms = np.linalg.norm(vectors, axis=1)
    l2_min = float(np.min(l2_norms))
    l2_mean = float(np.mean(l2_norms))
    l2_max = float(np.max(l2_norms))

    row_id_unique_count = len(set(row_ids))

    return SemanticAudit(
        rows=vectors.shape[0],
        dim=vectors.shape[1],
        dtype=str(vectors.dtype),
        non_finite_count=non_finite_count,
        zero_norm_count=zero_norm_count,
        l2_min=l2_min,
        l2_mean=l2_mean,
        l2_max=l2_max,
        row_id_unique_count=row_id_unique_count,
        alignment_ok=(row_id_unique_count == expected_rows),
        view=bundle.view,
    )

def build_node_table(bundle: SemanticBundle, records_path: str | Path) -> pd.DataFrame:
    records_df = pd.read_parquet(records_path)

    record_id_to_info = {}
    for _, row in records_df.iterrows():
        record_id_to_info[row["record_id"]] = {
            "stock_code": row["stock_code"],
            "stock_name": row["stock_name"],
            "asof_date": row["asof_date"],
        }

    nodes = []
    for node_id, record_id in enumerate(bundle.row_ids):
        info = record_id_to_info[record_id]
        nodes.append({
            "node_id": node_id,
            "record_id": record_id,
            "stock_code": info["stock_code"],
            "stock_name": info["stock_name"],
            "asof_date": info["asof_date"],
            "semantic_view": bundle.view,
        })

    return pd.DataFrame(nodes)