import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config, load_semantic_view, build_node_table
from semantic_graph_research.cache_io import read_cache_manifest

def test_real_node_alignment():
    config_path = Path(__file__).parent.parent / "configs" / "phase1_semantic_graph.yaml"
    config = load_config(config_path)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]

    if not cache_dirs:
        pytest.skip("No cache found, run T1 and T2 first")

    cache_dir = sorted(cache_dirs)[-1]
    manifest = read_cache_manifest(cache_dir)

    if "nodes_count" not in manifest:
        pytest.skip("Nodes not built yet, run T2 first")

    bundle = load_semantic_view(config)
    nodes = build_node_table(bundle, config["semantic"]["records_path"])

    assert len(nodes) == 5502, f"nodes should have 5502 rows, got {len(nodes)}"
    assert nodes["node_id"].min() == 0, "node_id should start from 0"
    assert nodes["node_id"].max() == 5501, "node_id should end at 5501"
    assert nodes["node_id"].nunique() == 5502, "node_id should be unique"
    assert nodes["record_id"].nunique() == 5502, "record_id should be unique"
    assert nodes["stock_code"].nunique() == 5502, "stock_code should be unique"

    assert set(nodes.columns) == {"node_id", "record_id", "stock_code", "stock_name", "asof_date", "semantic_view"}

    assert (nodes["node_id"] == list(range(5502))).all(), "node_id should be 0-5501 consecutive"

if __name__ == "__main__":
    test_real_node_alignment()
    print("test_real_node_alignment: PASSED")