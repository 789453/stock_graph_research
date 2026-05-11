import os
import pandas as pd
import numpy as np
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint

def map_valuation_style(row):
    pe = row["pe_ttm"]
    pb = row["pb"]
    is_large = row["total_mv"] > row["total_mv_median"]
    
    if not row["pe_ttm_valid"] or not row["pb_valid"]:
        return "negative_or_invalid_pe_pb"
    
    pb_high = pb > row["pb_median"]
    
    if is_large and pb_high: return "large_high_pb"
    if is_large and not pb_high: return "large_low_pb"
    if not is_large and pb_high: return "small_high_pb"
    if not is_large and not pb_high: return "small_low_pb"
    return "normal"

def main():
    run_id = get_run_id()
    
    # Inputs
    industry_profile_path = f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_industry_profile.parquet"
    daily_basic_path = "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily_basic.parquet"
    
    print("Loading data...")
    node_industry = pd.read_parquet(industry_profile_path)
    
    # Read only relevant columns to save memory, and filter by trade_date <= 20260423
    import duckdb
    query = """
    SELECT * FROM read_parquet('/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily_basic.parquet')
    WHERE trade_date <= '20260423'
    """
    daily_basic = duckdb.query(query).df()
    
    # 1. Get latest valid snapshot per stock
    print("Extracting latest snapshot...")
    daily_basic = daily_basic.sort_values(["ts_code", "trade_date"])
    
    # We want the latest non-null for key metrics
    # Simple approach: group by ts_code, forward fill, then take the last row
    daily_basic_ffill = daily_basic.groupby("ts_code").ffill()
    daily_basic_ffill["ts_code"] = daily_basic["ts_code"]
    daily_basic_ffill["trade_date"] = daily_basic["trade_date"]
    
    snapshot = daily_basic_ffill.groupby("ts_code").last().reset_index()
    snapshot = snapshot.rename(columns={"trade_date": "snapshot_trade_date"})
    
    # 2. Join to nodes
    print("Joining to nodes...")
    node_fundamental = node_industry[["node_id", "ts_code"]].merge(snapshot, on="ts_code", how="left")
    
    # 3. Derived variables
    print("Computing derived variables...")
    node_fundamental["pe_ttm_valid"] = (node_fundamental["pe_ttm"] > 0) & node_fundamental["pe_ttm"].notna()
    node_fundamental["pb_valid"] = (node_fundamental["pb"] > 0) & node_fundamental["pb"].notna()
    
    node_fundamental["log_total_mv"] = np.log(node_fundamental["total_mv"].clip(lower=1))
    node_fundamental["log_circ_mv"] = np.log(node_fundamental["circ_mv"].clip(lower=1))
    
    # Buckets (using qcut for quantiles)
    for col, new_col in [("total_mv", "market_cap_bucket"), 
                         ("circ_mv", "circ_mv_bucket"),
                         ("pe_ttm", "pe_ttm_bucket"),
                         ("pb", "pb_bucket"),
                         ("turnover_rate", "turnover_bucket")]:
        # Only bucket valid values
        valid_mask = node_fundamental[col].notna()
        if col in ["pe_ttm", "pb"]:
            valid_mask = valid_mask & (node_fundamental[col] > 0)
            
        node_fundamental.loc[valid_mask, new_col] = pd.qcut(node_fundamental.loc[valid_mask, col], q=5, labels=False, duplicates='drop')
    
    # Valuation style
    node_fundamental["total_mv_median"] = node_fundamental["total_mv"].median()
    node_fundamental["pb_median"] = node_fundamental["pb"].median()
    node_fundamental["valuation_style"] = node_fundamental.apply(map_valuation_style, axis=1)
    node_fundamental = node_fundamental.drop(columns=["total_mv_median", "pb_median"])
    
    # Outputs
    fundamental_profile_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_fundamental_snapshot.parquet")
    fundamental_profile_path.parent.mkdir(parents=True, exist_ok=True)
    node_fundamental.to_parquet(fundamental_profile_path)
    
    # Validation summary
    val_summary = {
        "node_coverage": float(node_fundamental["ts_code"].notna().mean()),
        "total_mv_coverage": float(node_fundamental["total_mv"].notna().mean()),
        "pb_coverage": float(node_fundamental["pb"].notna().mean()),
        "negative_pe_count": int((node_fundamental["pe_ttm"] <= 0).sum()),
        "node_coverage_ok": bool(node_fundamental["ts_code"].notna().mean() >= 0.95),
        "total_mv_coverage_ok": bool(node_fundamental["total_mv"].notna().mean() >= 0.90),
        "pb_coverage_ok": bool(node_fundamental["pb"].notna().mean() >= 0.80)
    }
    
    # Manifest
    manifest = create_manifest(
        task_id="t04",
        task_name="fundamental_profile",
        status="success",
        inputs=[
            {"path": industry_profile_path, "fingerprint": get_file_fingerprint(industry_profile_path)},
            {"path": daily_basic_path, "fingerprint": get_file_fingerprint(daily_basic_path)}
        ],
        outputs=[
            {"path": str(fundamental_profile_path), "fingerprint": get_file_fingerprint(str(fundamental_profile_path))}
        ],
        validation=val_summary
    )
    save_manifest(manifest, run_id)
    print("Task 04 completed successfully.")

if __name__ == "__main__":
    main()
