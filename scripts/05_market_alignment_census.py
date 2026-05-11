#!/usr/bin/env python3
"""
T6 - 2010—2026.04 行情对齐普查
不做因子，只确认图节点能否接入后续行情研究
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest

def main():
    parser = argparse.ArgumentParser(description="T6: 2010—2026.04 行情对齐普查")
    parser.add_argument("--config", default="configs/phase1_semantic_graph.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T6: 行情对齐普查")
    print(f"Config: {args.config}")
    print("=" * 60)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    if args.cache_key:
        cache_dir = cache_root / args.cache_key
    else:
        cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
        if not cache_dirs:
            print("[FAIL] 未找到缓存")
            sys.exit(1)
        cache_dir = sorted(cache_dirs)[-1]

    if not cache_dir.exists():
        print(f"[FAIL] 缓存目录不存在: {cache_dir}")
        sys.exit(1)

    manifest = read_cache_manifest(cache_dir)
    print(f"[OK] 读取语义图缓存: {cache_dir}")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    node_stock_codes = set(nodes["stock_code"].tolist())
    print(f"[OK] 节点股票数: {len(node_stock_codes)}")

    requested_start = config["market"]["requested_start_date"]
    requested_end = config["market"]["requested_end_date"]
    print(f"[INFO] 请求窗口: {requested_start} 至 {requested_end}")

    market_cache_root = Path(config["cache"]["root"]) / "market_alignment"
    market_cache_dir = market_cache_root / cache_dir.name
    market_cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] 行情缓存目录: {market_cache_dir}")

    print("\n--- 处理 stock_daily ---")
    stock_daily_path = Path(config["market"]["stock_daily_path"])
    if not stock_daily_path.exists():
        print(f"[WARN] stock_daily 不存在: {stock_daily_path}")
        daily_coverage = pd.DataFrame(columns=["ts_code", "daily_row_count", "first_trade_date", "last_trade_date"])
        actual_max_date = "unknown"
    else:
        # 使用更高效的方式读取或处理大数据
        # 这里为了演示仍使用全量读取，实际项目中建议用 duckdb 或 dask
        stock_daily = pd.read_parquet(stock_daily_path)
        print(f"[OK] stock_daily 加载: {len(stock_daily)} rows")

        daily_by_stock = stock_daily.groupby("ts_code").agg(
            daily_row_count=("trade_date", "count"),
            first_trade_date=("trade_date", "min"),
            last_trade_date=("trade_date", "max"),
        ).reset_index()

        actual_max_date = str(stock_daily["trade_date"].max())
        print(f"[INFO] 实际数据最大日期: {actual_max_date}")

        daily_coverage = daily_by_stock[daily_by_stock["ts_code"].isin(node_stock_codes)]
        print(f"[OK] 节点覆盖: {len(daily_coverage)} / {len(node_stock_codes)}")

    print("\n--- 处理 stock_daily_basic ---")
    stock_daily_basic_path = Path(config["market"]["stock_daily_basic_path"])
    if not stock_daily_basic_path.exists():
        print(f"[WARN] stock_daily_basic 不存在: {stock_daily_basic_path}")
        basic_coverage = pd.DataFrame(columns=["ts_code", "daily_basic_row_count"])
    else:
        stock_daily_basic = pd.read_parquet(stock_daily_basic_path)
        print(f"[OK] stock_daily_basic 加载: {len(stock_daily_basic)} rows")

        basic_by_stock = stock_daily_basic.groupby("ts_code").agg(
            daily_basic_row_count=("trade_date", "count"),
        ).reset_index()

        basic_coverage = basic_by_stock[basic_by_stock["ts_code"].isin(node_stock_codes)]
        print(f"[OK] 节点覆盖: {len(basic_coverage)} / {len(node_stock_codes)}")

    print("\n--- 合并覆盖率 ---")
    coverage = pd.DataFrame({"ts_code": list(node_stock_codes)})
    coverage = coverage.merge(daily_coverage, on="ts_code", how="left")
    coverage = coverage.merge(basic_coverage, on="ts_code", how="left")
    
    coverage["daily_row_count"] = coverage["daily_row_count"].fillna(0)
    coverage["daily_basic_row_count"] = coverage["daily_basic_row_count"].fillna(0)
    coverage["has_daily"] = coverage["daily_row_count"] > 0
    coverage["has_daily_basic"] = coverage["daily_basic_row_count"] > 0
    
    # 增加缺失原因分析
    def missing_reason(row):
        if row["daily_row_count"] == 0:
            return "missing_daily"
        if row["daily_basic_row_count"] == 0:
            return "missing_basic"
        return "ok"
    
    coverage["missing_reason"] = coverage.apply(missing_reason, axis=1)

    missing_stocks = coverage[coverage["missing_reason"] != "ok"]
    if len(missing_stocks) > 0:
        print(f"[WARN] {len(missing_stocks)} 只股票存在行情缺失")
        missing_stocks[["ts_code", "missing_reason"]].to_csv(market_cache_dir / "missing_stock_codes.csv", index=False)
        print(f"       缺失名单已保存至: {market_cache_dir / 'missing_stock_codes.csv'}")

    total_stocks = len(node_stock_codes)
    stocks_with_daily = coverage["has_daily"].sum()
    stocks_with_basic = coverage["has_daily_basic"].sum()

    summary = {
        "requested_start_date": requested_start,
        "requested_end_date": requested_end,
        "actual_data_max_date": actual_max_date,
        "total_nodes": total_stocks,
        "stocks_with_daily": int(stocks_with_daily),
        "stocks_with_daily_basic": int(stocks_with_basic),
        "stocks_with_daily_ratio": float(stocks_with_daily / total_stocks) if total_stocks > 0 else 0,
        "stocks_with_basic_ratio": float(stocks_with_basic / total_stocks) if total_stocks > 0 else 0,
        "missing_count": int(len(missing_stocks)),
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "script": "05_market_alignment_census.py",
    }

    # 强断言：覆盖率必须达到 95%
    print("[INFO] 正在执行覆盖率断言...")
    assert summary["stocks_with_daily_ratio"] >= 0.95, f"Daily 行情覆盖率不足 95%: {summary['stocks_with_daily_ratio']:.2%}"
    print("[OK] 覆盖率断言通过")

    print("\n--- 覆盖率摘要 ---")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    coverage.to_parquet(market_cache_dir / "market_coverage_by_stock.parquet", index=False)
    print(f"[OK] coverage 已保存: {market_cache_dir / 'market_coverage_by_stock.parquet'}")

    with open(market_cache_dir / "market_coverage_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] summary 已保存: {market_cache_dir / 'market_coverage_summary.json'}")

    market_manifest = {
        "task": "T6",
        "semantic_cache_key": cache_dir.name,
        "requested_window": f"{requested_start}_{requested_end}",
        "actual_max_date": summary["actual_data_max_date"],
        "coverage": summary,
    }
    with open(market_cache_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(market_manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T6 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()