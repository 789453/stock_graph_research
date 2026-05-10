import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def get_test_config():
    project_root = Path(__file__).parent.parent
    candidates = [
        project_root / "configs" / "phase1_semantic_graph.yaml",
        project_root / "configs" / "phase2_semantic_graph_research.yaml",
    ]
    for p in candidates:
        if p.exists():
            config = load_config(p)
            if "semantic" not in config:
                config["semantic"] = {
                    "vectors_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.npy",
                    "meta_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.meta.json",
                    "records_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/parquet/records-all.parquet",
                    "expected_rows": 5502,
                    "expected_dim": 1024,
                    "expected_dtype": "float32",
                    "allow_fallback": False,
                }
            return config
    raise FileNotFoundError("No config found")

from semantic_graph_research import load_config, load_semantic_view, audit_semantic_bundle

def test_real_semantic_contract():
    config = get_test_config()

    assert config["semantic"]["allow_fallback"] == False, "allow_fallback must be False"

    bundle = load_semantic_view(config)

    assert bundle.view == "application_scenarios_json", f"view should be application_scenarios_json, got {bundle.view}"
    assert bundle.rows == 5502, f"rows should be 5502, got {bundle.rows}"
    assert bundle.dim == 1024, f"dim should be 1024, got {bundle.dim}"

    audit = audit_semantic_bundle(bundle, config)

    assert audit.rows == 5502
    assert audit.dim == 1024
    assert audit.dtype == "float32"
    assert audit.non_finite_count == 0, f"non_finite_count should be 0, got {audit.non_finite_count}"
    assert audit.zero_norm_count == 0, f"zero_norm_count should be 0, got {audit.zero_norm_count}"
    assert audit.alignment_ok == True
    assert audit.view == "application_scenarios_json"

    vectors = bundle.vectors
    assert vectors.ndim == 2
    assert vectors.shape == (5502, 1024)
    assert np.isfinite(vectors).all()

if __name__ == "__main__":
    test_real_semantic_contract()
    print("test_real_semantic_contract: PASSED")