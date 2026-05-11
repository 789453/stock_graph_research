import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from scripts.phase2_3.utils import get_run_id

def test_edge_candidates_repaired_contract():
    run_id = get_run_id()
    path = Path(f"cache/semantic_graph/{run_id}/phase2_3/edge_metrics/edge_candidates_k100_repaired.parquet")
    assert path.exists(), f"Repaired edge table missing: {path}"
    
    df = pd.read_parquet(path)
    
    # 1. No self node edges
    assert (df["src_node_id"] != df["dst_node_id"]).all(), "Found self-node edges"
    
    # 2. No self stock edges
    assert (df["src_stock_code"] != df["dst_stock_code"]).all(), "Found self-stock edges"
    
    # 3. Rank range 1..100
    assert df["rank"].min() >= 1, "Rank too low"
    assert df["rank"].max() <= 100, "Rank too high"
    
    # 4. Scores finite
    assert np.isfinite(df["score"]).all(), "Non-finite scores found"
    
    # 5. Mutual edges consistency
    mutual = df[df["is_mutual"]]
    assert mutual["reverse_rank"].notna().all(), "Mutual edges missing reverse_rank"
    assert mutual["reverse_score"].notna().all(), "Mutual edges missing reverse_score"
    
    # 6. Mutual ratio check
    ratio = df["is_mutual"].mean()
    assert 0 < ratio < 1, f"Suspicious mutual ratio: {ratio}"
    
    # 7. Rank bands correct
    assert df["exclusive_rank_band"].nunique() >= 5, "Missing rank bands"
    assert "rank_001_005" in df["exclusive_rank_band"].unique()
    
    print("Edge candidates contract test passed.")

if __name__ == "__main__":
    test_edge_candidates_repaired_contract()
