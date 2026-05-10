import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any

def read_market_profile_with_duckdb(
    stock_daily_basic_path: str,
    stock_daily_path: str,
    stock_codes: list[str],
    start_date: str = "20180101",
    end_date: str = "20260423",
) -> pd.DataFrame:
    import duckdb
    import pandas as pd

    con = duckdb.connect()
    codes_df = pd.DataFrame({"ts_code": stock_codes})
    con.register("codes", codes_df)

    print(f"Executing DuckDB median query for MV and Turnover...")
    basic = con.execute(f'''
        SELECT
            b.ts_code,
            median(b.total_mv) AS median_total_mv,
            median(b.circ_mv) AS median_circ_mv,
            median(b.turnover_rate) AS median_turnover_rate
        FROM read_parquet('{stock_daily_basic_path}') b
        INNER JOIN codes c ON b.ts_code = c.ts_code
        WHERE b.trade_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY b.ts_code
    ''').df()

    print(f"Executing DuckDB median query for Amount...")
    daily = con.execute(f'''
        SELECT
            d.ts_code,
            median(d.amount) AS median_amount
        FROM read_parquet('{stock_daily_path}') d
        INNER JOIN codes c ON d.ts_code = c.ts_code
        WHERE d.trade_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY d.ts_code
    ''').df()

    return basic.merge(daily, on="ts_code", how="outer", validate="one_to_one")

def run_market_profile_repair(global_config: dict[str, Any]):
    start_time = time.time()
    print("Starting market profile repair (T2.1.5)...")
    
    daily_basic_path = global_config["market_data"]["stock_daily_basic_path"]
    daily_path = global_config["market_data"]["stock_daily_path"]
    records_path = global_config["records"]["records_path"]
    
    records = pd.read_parquet(records_path)
    stock_codes = records["stock_code"].unique().tolist()
    
    profile = read_market_profile_with_duckdb(
        daily_basic_path, 
        daily_path, 
        stock_codes,
        start_date=global_config["project"]["start_date"],
        end_date=global_config["project"]["end_date"]
    )
    
    # Add log values
    profile["log_total_mv"] = np.log1p(profile["median_total_mv"])
    profile["log_amount"] = np.log1p(profile["median_amount"])
    
    # Binning (10 buckets)
    print("Assigning buckets...")
    for col in ["median_total_mv", "median_circ_mv", "median_turnover_rate", "median_amount"]:
        bucket_col = col.replace("median_", "") + "_bucket_10"
        profile[bucket_col] = pd.qcut(profile[col], 10, labels=False, duplicates="drop")
        
    # Merge back to all stock_codes to see who is missing
    full_profile = pd.DataFrame({"stock_code": stock_codes})
    full_profile = full_profile.merge(profile, left_on="stock_code", right_on="ts_code", how="left")
    full_profile.drop(columns=["ts_code"], inplace=True)
    
    matched_count = full_profile["median_total_mv"].notna().sum()
    print(f"Matched {matched_count} / {len(stock_codes)} stocks with market data.")
    
    # Strong Validation
    min_required = global_config["baselines"]["min_market_matched_nodes"]
    if matched_count < min_required:
        raise ValueError(f"market matched nodes too low: {matched_count}, expected >= {min_required}")
    
    status = "success"
    
    # Paths
    out_path = Path("cache/semantic_graph/multi_view/baselines")
    out_path.mkdir(parents=True, exist_ok=True)
    
    full_profile.to_parquet(out_path / "node_size_liquidity_profile.parquet", compression="zstd")
    
    summary = {
        "matched_market_nodes": int(matched_count),
        "unmatched_nodes": int(len(stock_codes) - matched_count),
        "min_required_matched_nodes": min_required,
        "status": status,
        "fields": [
            "median_total_mv",
            "median_circ_mv",
            "median_turnover_rate",
            "median_amount"
        ],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    }
    
    with open(out_path / "size_liquidity_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    # Report
    report_dir = Path("outputs/reports/phase2_1")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    unmatched_samples = full_profile[full_profile["median_total_mv"].isna()]["stock_code"].head(20).tolist()
    
    report_md = f"""# Size/Liquidity Profile Repair Report (T2.1.5)

## 1. Summary
- **Status**: {status.upper()}
- **Matched Market Nodes**: {matched_count} / {len(stock_codes)}
- **Min Required**: {min_required}
- **Timestamp**: {summary['timestamp']}

## 2. Bucket Statistics
| Field | Count | Min | Median | Max |
|---|---|---|---|---|
| total_mv | {profile['median_total_mv'].count()} | {profile['median_total_mv'].min():.2f} | {profile['median_total_mv'].median():.2f} | {profile['median_total_mv'].max():.2f} |
| amount | {profile['median_amount'].count()} | {profile['median_amount'].min():.2f} | {profile['median_amount'].median():.2f} | {profile['median_amount'].max():.2f} |

## 3. Missing Data
- **Unmatched count**: {summary['unmatched_nodes']}
- **Unmatched samples**: {", ".join(unmatched_samples)}

## 4. Conclusion
{"✅ Alignment criteria met. Ready for baseline research." if status == "success" else "❌ Alignment criteria NOT met. Please check data source paths."}
"""
    with open(report_dir / "size_liquidity_repair_report.md", "w") as f:
        f.write(report_md)
        
    if status == "failed":
        print(f"ERROR: Only matched {matched_count} stocks, required {min_required}")
        # In Agent mode, we keep going but record the failure
        
    print(f"Market profile repair finished with status: {status}")
    return summary

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    run_market_profile_repair(config)

if __name__ == "__main__":
    main()
