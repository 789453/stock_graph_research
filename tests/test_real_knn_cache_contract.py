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

from semantic_graph_research import load_config, load_semantic_view, build_faiss_knn
from semantic_graph_research.cache_io import read_cache_manifest

def test_real_knn_cache_contract():
    config = get_test_config()

    cache_root = Path(__file__).parent.parent / "cache" / "semantic_graph"
    cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]

    if not cache_dirs:
        pytest.skip("No cache found, run T1-T3 first")

    cache_dir = sorted(cache_dirs)[-1]

    k_values = [10, 20, 50]
    for k in k_values:
        neighbors_path = cache_dir / f"neighbors_k{k}.npz"
        assert neighbors_path.exists(), f"neighbors_k{k}.npz should exist"

        data = np.load(neighbors_path)
        assert "indices" in data, f"indices should be in neighbors_k{k}.npz"
        assert "scores" in data, f"scores should be in neighbors_k{k}.npz"

        indices = data["indices"]
        scores = data["scores"]

        assert indices.shape == (5502, k), f"indices shape should be (5502, {k}), got {indices.shape}"
        assert scores.shape == (5502, k), f"scores shape should be (5502, {k}), got {scores.shape}"
        assert indices.dtype == np.int32, f"indices dtype should be int32, got {indices.dtype}"
        assert scores.dtype == np.float32, f"scores dtype should be float32, got {scores.dtype}"

        for i in range(5502):
            assert i not in indices[i], f"self-neighbor should be removed for node {i}"

        assert np.isfinite(scores).all(), f"scores should be all finite for k={k}"

if __name__ == "__main__":
    test_real_knn_cache_contract()
    print("test_real_knn_cache_contract: PASSED")