import pytest
import sys
from pathlib import Path
from unittest.mock import patch

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

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest

def test_plotting_reads_cache_only():
    config = get_test_config()

    cache_root = Path(__file__).parent.parent / "cache" / "semantic_graph"
    cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]

    if not cache_dirs:
        pytest.skip("No cache found, run T1-T5 first")

    cache_dir = sorted(cache_dirs)[-1]

    assert (cache_dir / "nodes.parquet").exists(), "nodes.parquet should exist"
    assert (cache_dir / "edges_directed_k20.parquet").exists(), "edges_directed_k20.parquet should exist"
    assert (cache_dir / "graph_stats_k20.json").exists(), "graph_stats_k20.json should exist"

    with patch("numpy.load") as mock_load:
        from semantic_graph_research.plotting import plot_score_distribution_from_cache
        output_dir = Path(__file__).parent.parent / "outputs" / "plots"
        output_dir.mkdir(parents=True, exist_ok=True)

        plot_score_distribution_from_cache(cache_dir, output_dir)

        assert not mock_load.called, "plotting should not call np.load for raw NPY"

if __name__ == "__main__":
    test_plotting_reads_cache_only()
    print("test_plotting_reads_cache_only: PASSED")