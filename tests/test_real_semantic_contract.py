import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config, load_semantic_view, audit_semantic_bundle

def test_real_semantic_contract():
    config_path = Path(__file__).parent.parent / "configs" / "phase1_semantic_graph.yaml"
    config = load_config(config_path)

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