#!/usr/bin/env python3
"""
T2.7: 2018-2026 市场行为面板
计算每个节点股票在研究窗口内的年度收益、波动率、换手率等市场行为指标
"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    project_root = Path(__file__).parent.parent
    cache_dir = project_root / "cache" / "semantic_graph" / "2eebde04e582"
    phase2_cache = cache_dir / "phase2"
    market_behavior_cache = phase2_cache / "market_behavior"
    market_behavior_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = project_root / "outputs" / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("T2.7: 2018-2026 市场行为面板")
    print("=" * 60)

    import pandas as pd
    import numpy as np

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    stock_codes = nodes["stock_code"].tolist()

    print("\n[Step 1] 加载 stock_daily...")
    stock_daily_path = Path("/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily.parquet")
    if not stock_daily_path.exists():
        print("[FAIL] stock_daily 不存在")
        sys.exit(1)

    stock_daily = pd.read_parquet(stock_daily_path)
    print(f"[OK] stock_daily: {len(stock_daily)} rows")
    print(f"  日期范围: {stock_daily['trade_date'].min()} - {stock_daily['trade_date'].max()}")

    print("\n[Step 2] 过滤到节点股票...")
    stock_daily = stock_daily[stock_daily["ts_code"].isin(stock_codes)]
    print(f"[OK] 过滤后: {len(stock_daily)} rows")

    print("\n[Step 3] 过滤研究窗口 2018-2026...")
    stock_daily["trade_date_int"] = stock_daily["trade_date"].astype(int)
    stock_daily = stock_daily[
        (stock_daily["trade_date_int"] >= 20180101) &
        (stock_daily["trade_date_int"] <= 20261231)
    ]
    stock_daily = stock_daily.drop(columns=["trade_date_int"])
    print(f"[OK] 过滤后: {len(stock_daily)} rows")

    print("\n[Step 4] 计算年度市场行为指标...")
    stock_daily = stock_daily.sort_values(["ts_code", "trade_date"])
    stock_daily["trade_date_int"] = stock_daily["trade_date"].astype(int)

    annual_stats = []
    for year in range(2018, 2027):
        year_data = stock_daily[
            (stock_daily["trade_date_int"] >= year * 10000) &
            (stock_daily["trade_date_int"] < (year + 1) * 10000)
        ]
        if len(year_data) == 0:
            continue

        for ts_code, group in year_data.groupby("ts_code"):
            group = group.sort_values("trade_date")
            prices = group["close"].values

            if len(prices) >= 2:
                annual_return = (prices[-1] / prices[0]) - 1 if prices[0] > 0 else np.nan
                log_returns = np.diff(np.log(prices))
                volatility = float(np.std(log_returns)) if len(log_returns) > 0 else np.nan
                mean_volume = float(np.mean(group["vol"].values)) if "vol" in group.columns else np.nan
                mean_amount = float(np.mean(group["amount"].values)) if "amount" in group.columns else np.nan
                max_drawdown = float(np.min(prices / np.maximum.accumulate(prices) - 1)) if len(prices) > 0 else np.nan
                trading_days = len(group)
            else:
                annual_return = np.nan
                volatility = np.nan
                mean_volume = np.nan
                mean_amount = np.nan
                max_drawdown = np.nan
                trading_days = len(group)

            annual_stats.append({
                "ts_code": ts_code,
                "year": year,
                "annual_return": round(annual_return, 4) if not np.isnan(annual_return) else np.nan,
                "volatility": round(volatility, 4) if not np.isnan(volatility) else np.nan,
                "mean_volume": round(mean_volume, 2) if not np.isnan(mean_volume) else np.nan,
                "mean_amount": round(mean_amount, 2) if not np.isnan(mean_amount) else np.nan,
                "max_drawdown": round(max_drawdown, 4) if not np.isnan(max_drawdown) else np.nan,
                "trading_days": trading_days,
            })

    panel_df = pd.DataFrame(annual_stats)
    print(f"[OK] 年度面板: {len(panel_df)} records, {panel_df['year'].nunique()} years")

    print("\n[Step 5] 计算节点平均市场行为...")
    node_market_stats = panel_df.groupby("ts_code").agg(
        avg_annual_return=("annual_return", "mean"),
        avg_volatility=("volatility", "mean"),
        avg_mean_amount=("mean_amount", "mean"),
        total_trading_days=("trading_days", "sum"),
    ).reset_index()

    node_panel = nodes.merge(node_market_stats, left_on="stock_code", right_on="ts_code", how="left")
    node_panel = node_panel.drop(columns=["ts_code"], errors="ignore")

    print(f"[OK] 节点面板: {len(node_panel)} nodes")

    print("\n[Step 6] 市场行为统计...")
    market_stats = {
        "avg_annual_return": {
            "mean": round(float(node_panel["avg_annual_return"].mean()), 4),
            "median": round(float(node_panel["avg_annual_return"].median()), 4),
            "std": round(float(node_panel["avg_annual_return"].std()), 4),
        },
        "avg_volatility": {
            "mean": round(float(node_panel["avg_volatility"].mean()), 4),
            "median": round(float(node_panel["avg_volatility"].median()), 4),
            "std": round(float(node_panel["avg_volatility"].std()), 4),
        },
    }
    print(json.dumps(market_stats, indent=2))

    print("\n[Step 7] 保存结果...")
    panel_df.to_parquet(market_behavior_cache / "annual_market_panel_2018_2026.parquet", index=False)
    print(f"[OK] annual_market_panel_2018_2026.parquet 已保存: {len(panel_df)} records")

    node_panel.to_parquet(market_behavior_cache / "node_market_panel_2018_2026.parquet", index=False)
    print(f"[OK] node_market_panel_2018_2026.parquet 已保存: {len(node_panel)} nodes")

    summary = {
        "total_nodes": int(len(nodes)),
        "nodes_with_market_data": int(node_panel["avg_annual_return"].notna().sum()),
        "years_covered": list(range(2018, 2027)),
        "annual_panel_records": int(len(panel_df)),
        "market_stats": market_stats,
    }

    summary_path = market_behavior_cache / "market_behavior_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] market_behavior_summary.json 已保存")

    manifest = {
        "task_id": "T2.7",
        "task_name": "Market behavior panel 2018-2026",
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "inputs": [str(stock_daily_path)],
        "outputs": [
            str(market_behavior_cache / "annual_market_panel_2018_2026.parquet"),
            str(market_behavior_cache / "node_market_panel_2018_2026.parquet"),
            str(summary_path),
        ],
        "parameters": {"window": "2018-2026"},
        "warnings": [],
        "error": None,
    }

    with open(manifests_dir / "t27_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.7 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()