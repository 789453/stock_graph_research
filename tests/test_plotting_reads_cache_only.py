import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest

def test_plotting_reads_cache_only():
    config_path = Path(__file__).parent.parent / "configs" / "phase1_semantic_graph.yaml"
    config = load_config(config_path)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]

    if not cache_dirs:
        pytest.skip("No cache found, run T1-T5 first")

    cache_dir = sorted(cache_dirs)[-1]

    assert (cache_dir / "nodes.parquet").exists(), "nodes.parquet should exist"
    assert (cache_dir / f"edges_directed_k20.parquet").exists(), "edges_directed_k20.parquet should exist"
    assert (cache_dir / f"graph_stats_k20.json").exists(), "graph_stats_k20.json should exist"

    with patch("numpy.load") as mock_load:
        from semantic_graph_research.plotting import plot_score_distribution_from_cache
        output_dir = Path(config["plots"]["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        plot_score_distribution_from_cache(cache_dir, output_dir)

        assert not mock_load.called, "plotting should not call np.load for raw NPY"

if __name__ == "__main__":
    test_plotting_reads_cache_only()
    print("test_plotting_reads_cache_only: PASSED")