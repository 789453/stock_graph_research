import pytest
import pandas as pd
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

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest

def test_market_alignment_contract():
    config = get_test_config()

    market_cache_root = Path(__file__).parent.parent / "cache" / "market_alignment"
    market_cache_dirs = [d for d in market_cache_root.iterdir() if d.is_dir()]

    if not market_cache_dirs:
        pytest.skip("No market cache found, run T6 first")

    market_cache_dir = sorted(market_cache_dirs)[-1]

    coverage_path = market_cache_dir / "market_coverage_by_stock.parquet"
    assert coverage_path.exists(), "market_coverage_by_stock.parquet should exist"

    summary_path = market_cache_dir / "market_coverage_summary.json"
    assert summary_path.exists(), "market_coverage_summary.json should exist"

    coverage = pd.read_parquet(coverage_path)

    expected_cols = ["ts_code", "daily_row_count", "first_trade_date", "last_trade_date", "has_daily"]
    for col in expected_cols:
        assert col in coverage.columns, f"column {col} should be in coverage"

    import json
    with open(summary_path) as f:
        summary = json.load(f)

    assert "requested_start_date" in summary
    assert "requested_end_date" in summary
    assert "actual_data_max_date" in summary
    assert "total_nodes" in summary
    assert "no补造" in summary
    assert summary["no补造"] == True

if __name__ == "__main__":
    test_market_alignment_contract()
    print("test_market_alignment_contract: PASSED")