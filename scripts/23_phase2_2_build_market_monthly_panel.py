import os
import json
import time
import numpy as np
import pandas as pd
import yaml
import duckdb
from pathlib import Path
from typing import Any

def build_monthly_panel(global_config: dict[str, Any]):
    start_time = time.time()
    print("Starting T2.2.3: Building Monthly Market Panel...")
    
    daily_path = global_config["market_data"]["stock_daily_path"]
    daily_basic_path = global_config["market_data"]["stock_daily_basic_path"]
    records_path = global_config["records"]["records_path"]
    
    start_date = global_config["project"]["start_date"]
    end_date = global_config["project"]["end_date"]
    
    # Load records to get stock codes
    records = pd.read_parquet(records_path)
    stock_codes = records["stock_code"].unique().tolist()
    
    con = duckdb.connect()
    codes_df = pd.DataFrame({"ts_code": stock_codes})
    con.register("codes", codes_df)
    
    # 1. Calculate basic monthly stats using DuckDB
    print("Executing DuckDB monthly aggregation...")
    # Note: monthly_return = (last adj_close) / (last adj_close of previous month) - 1
    # We'll calculate it in two steps: first daily stats, then monthly join.
    
    query = f'''
    WITH daily_stats AS (
        SELECT 
            d.ts_code,
            d.trade_date,
            strftime(strptime(d.trade_date, '%Y%m%d'), '%Y-%m') as month,
            d.adj_close,
            d.amount,
            b.turnover_rate,
            -- daily return for volatility calculation
            (d.adj_close / LAG(d.adj_close) OVER (PARTITION BY d.ts_code ORDER BY d.trade_date)) - 1 as daily_ret
        FROM read_parquet('{daily_path}') d
        JOIN read_parquet('{daily_basic_path}') b ON d.ts_code = b.ts_code AND d.trade_date = b.trade_date
        INNER JOIN codes c ON d.ts_code = c.ts_code
        WHERE d.trade_date BETWEEN '{start_date}' AND '{end_date}'
    ),
    monthly_base AS (
        SELECT 
            ts_code,
            month,
            LAST_VALUE(adj_close) OVER (PARTITION BY ts_code, month ORDER BY trade_date RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_adj_close,
            -- First value of adj_close in the month is not enough, we need last of PREVIOUS month.
            -- We'll handle return calculation in python or a separate join.
            AVG(amount) as monthly_amount,
            AVG(turnover_rate) as monthly_turnover,
            STDDEV(daily_ret) as monthly_volatility,
            COUNT(trade_date) as valid_trading_days
        FROM daily_stats
        GROUP BY ts_code, month, adj_close, trade_date -- This is wrong, should be group by ts_code, month
    )
    SELECT * FROM monthly_base
    '''
    
    # Correcting the query
    query = f'''
    WITH daily_data AS (
        SELECT 
            d.ts_code,
            d.trade_date,
            strftime(strptime(d.trade_date, '%Y%m%d'), '%Y-%m') as month,
            d.close,
            d.amount,
            d.pct_chg,
            b.turnover_rate
        FROM read_parquet('{daily_path}') d
        JOIN read_parquet('{daily_basic_path}') b ON d.ts_code = b.ts_code AND d.trade_date = b.trade_date
        INNER JOIN codes c ON d.ts_code = c.ts_code
        WHERE d.trade_date BETWEEN '{start_date}' AND '{end_date}'
    ),
    monthly_agg AS (
        SELECT 
            ts_code,
            month,
            exp(sum(ln(1 + pct_chg/100))) - 1 as monthly_return,
            AVG(amount) as monthly_amount,
            AVG(turnover_rate) as monthly_turnover,
            STDDEV(pct_chg/100) as monthly_volatility,
            COUNT(trade_date) as valid_trading_days
        FROM daily_data
        GROUP BY ts_code, month
    )
    SELECT * FROM monthly_agg
    '''
    
    panel = con.execute(query).df()
    
    # Calculate log returns
    panel["monthly_log_return"] = np.log1p(panel["monthly_return"])
    
    # Cross-sectional z-scores and flags
    print("Calculating cross-sectional metrics...")
    
    def calc_z(group, col):
        m = group[col].mean()
        s = group[col].std()
        return (group[col] - m) / np.maximum(s, 1e-12)

    def calc_flags(group):
        # Extreme up/down (top/bottom 5%)
        ret = group["monthly_return"]
        group["extreme_up_flag"] = ret >= ret.quantile(0.95)
        group["extreme_down_flag"] = ret <= ret.quantile(0.05)
        
        # Shock flags (z > 2)
        group["monthly_amount_z"] = calc_z(group, "monthly_amount")
        group["monthly_turnover_z"] = calc_z(group, "monthly_turnover")
        group["amount_shock_flag"] = group["monthly_amount_z"] > 2.0
        group["turnover_shock_flag"] = group["monthly_turnover_z"] > 2.0
        return group

    panel = panel.groupby("month", group_keys=False).apply(calc_flags)
    
    # Final cleanup
    panel.rename(columns={"ts_code": "stock_code"}, inplace=True)
    panel = panel.sort_values(["stock_code", "month"])
    
    # Save outputs
    out_dir = Path("cache/semantic_graph/phase2_2/market_panel")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    panel.to_parquet(out_dir / "node_monthly_panel.parquet", compression="zstd")
    
    # Summary
    n_stocks = panel["stock_code"].nunique()
    n_months = panel["month"].nunique()
    
    summary = {
        "n_stocks": int(n_stocks),
        "n_months": int(n_months),
        "start_month": panel["month"].min(),
        "end_month": panel["month"].max(),
        "total_rows": len(panel),
        "avg_stocks_per_month": float(panel.groupby("month")["stock_code"].count().mean()),
        "missing_return_ratio": float(panel["monthly_return"].isna().mean()),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    }
    
    with open(out_dir / "node_monthly_panel_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_2",
        "task_id": "T2.2.3",
        "task_name": "build_market_monthly_panel",
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "inputs": [daily_path, daily_basic_path, records_path],
        "outputs": [str(out_dir / "node_monthly_panel.parquet")],
        "row_counts": summary,
        "safe_to_continue": True
    }
    
    master_dir = Path("cache/semantic_graph/phase2_2/manifests")
    master_dir.mkdir(parents=True, exist_ok=True)
    with open(master_dir / "T2_2_3_panel_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Monthly panel built: {n_stocks} stocks, {n_months} months.")
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    build_monthly_panel(config)

if __name__ == "__main__":
    main()
