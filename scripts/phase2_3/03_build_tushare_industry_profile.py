import os
import pandas as pd
import numpy as np
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint

def map_board_group(market):
    if pd.isna(market): return "unknown"
    market = market.lower()
    if "主板" in market: return "main_board"
    if "创业板" in market: return "ChiNext"
    if "科创板" in market: return "STAR"
    if "北交所" in market: return "BSE"
    if "cdr" in market: return "CDR"
    return "unknown"

def main():
    run_id = get_run_id()
    
    # Inputs
    nodes_path = "cache/semantic_graph/2eebde04e582/nodes.parquet"
    sw_member_path = "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet"
    basic_snapshot_path = "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_basic_snapshot.parquet"
    
    print("Loading data...")
    nodes = pd.read_parquet(nodes_path)
    sw_member = pd.read_parquet(sw_member_path)
    basic_snapshot = pd.read_parquet(basic_snapshot_path)
    
    # 1. Normalize stock key to ts_code
    print("Normalizing stock keys...")
    # nodes has 'stock_code' which already includes suffix (e.g. 000001.SZ)
    # So ts_code is just stock_code
    nodes["ts_code"] = nodes["stock_code"]
    
    # 2. Deduplicate stock_sw_member
    print("Deduplicating SW member data...")
    sw_member = sw_member.sort_values(["ts_code", "in_date"], ascending=[True, False])
    sw_member["sw_member_duplicate_count"] = sw_member.groupby("ts_code")["ts_code"].transform("count")
    sw_member_dedup = sw_member.drop_duplicates("ts_code")
    
    # 3. Join semantic nodes to industry and snapshot
    print("Joining profiles...")
    node_industry = nodes.merge(sw_member_dedup[[
        "ts_code", "l1_code", "l1_name", "l2_code", "l2_name", "l3_code", "l3_name", "in_date", "sw_member_duplicate_count"
    ]], on="ts_code", how="left")
    
    node_snapshot = nodes.merge(basic_snapshot[[
        "ts_code", "symbol", "name", "area", "industry", "market", 
        "list_date", "act_name", "act_ent_type"
    ]], on="ts_code", how="left")
    
    # 4. Build listing_age_years
    print("Computing listing age and categorical groups...")
    # Use 20260423 as trade_date for snapshot age
    trade_date = pd.to_datetime("2026-04-23")
    node_snapshot["list_date_dt"] = pd.to_datetime(node_snapshot["list_date"], format="%Y%m%d", errors='coerce')
    node_snapshot["listing_age_years"] = (trade_date - node_snapshot["list_date_dt"]).dt.days / 365.25
    
    # 5. Create categorical groups
    node_snapshot["board_group"] = node_snapshot["market"].apply(map_board_group)
    node_snapshot["region_group"] = node_snapshot["area"]
    node_snapshot["ownership_group"] = node_snapshot["act_ent_type"]
    
    # Outputs
    industry_profile_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_industry_profile.parquet")
    snapshot_profile_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/data_profiles/node_basic_snapshot_profile.parquet")
    
    industry_profile_path.parent.mkdir(parents=True, exist_ok=True)
    node_industry.to_parquet(industry_profile_path)
    node_snapshot.to_parquet(snapshot_profile_path)
    
    # Data coverage table
    coverage_data = {
        "source": ["stock_sw_member", "stock_basic_snapshot"],
        "node_count": [len(nodes), len(nodes)],
        "matched_count": [node_industry["l1_code"].notna().sum(), node_snapshot["symbol"].notna().sum()],
    }
    coverage_df = pd.DataFrame(coverage_data)
    coverage_df["coverage_pct"] = coverage_df["matched_count"] / coverage_df["node_count"]
    coverage_table_path = Path(f"cache/semantic_graph/{run_id}/phase2_3/tables/table_01_data_coverage.csv")
    coverage_table_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_df.to_csv(coverage_table_path, index=False)
    
    # Manifest
    manifest = create_manifest(
        task_id="t03",
        task_name="industry_profile",
        status="success",
        inputs=[
            {"path": nodes_path, "fingerprint": get_file_fingerprint(nodes_path)},
            {"path": sw_member_path, "fingerprint": get_file_fingerprint(sw_member_path)},
            {"path": basic_snapshot_path, "fingerprint": get_file_fingerprint(basic_snapshot_path)}
        ],
        outputs=[
            {"path": str(industry_profile_path), "fingerprint": get_file_fingerprint(str(industry_profile_path))},
            {"path": str(snapshot_profile_path), "fingerprint": get_file_fingerprint(str(snapshot_profile_path))},
            {"path": str(coverage_table_path), "fingerprint": get_file_fingerprint(str(coverage_table_path))}
        ],
        validation={
            "industry_coverage_ok": bool(coverage_df.loc[0, "coverage_pct"] >= 0.95),
            "snapshot_coverage_ok": bool(coverage_df.loc[1, "coverage_pct"] >= 0.98),
            "industry_coverage": float(coverage_df.loc[0, "coverage_pct"]),
            "snapshot_coverage": float(coverage_df.loc[1, "coverage_pct"])
        }
    )
    save_manifest(manifest, run_id)
    print("Task 03 completed successfully.")

if __name__ == "__main__":
    main()
