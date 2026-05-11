import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest

def winsorize_s(s, lower=0.01, upper=0.99):
    if s.isna().all():
        return s
    lo, hi = s.quantile([lower, upper])
    return s.clip(lo, hi)

def main():
    parser = argparse.ArgumentParser(description="T2.4: 市值/流动性分域")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.4: 市值/流动性分域")
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

    phase2_cache = cache_dir / "phase2"
    baselines_cache = phase2_cache / "baselines"
    baselines_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = Path(config["plots"]["output_dir"]).parent / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    print("\n[Step 1] 加载 stock_daily_basic...")
    stock_daily_basic_path = Path(config["market"]["stock_daily_basic_path"])
    if not stock_daily_basic_path.exists():
        print("[WARN] stock_daily_basic 不存在，跳过流动性计算")
        nodes_with_market = nodes.copy()
        nodes_with_market["total_mv"] = np.nan
        nodes_with_market["turnover_rate"] = np.nan
    else:
        stock_daily_basic = pd.read_parquet(stock_daily_basic_path)
        print(f"[OK] stock_daily_basic: {len(stock_daily_basic)} rows")

        # 获取每个股票的最新数据（或指定日期的快照）
        latest_data = stock_daily_basic.sort_values("trade_date").groupby("ts_code").tail(1)
        print(f"[OK] 最新数据点: {len(latest_data)} stocks")

        nodes_with_market = nodes.merge(
            latest_data[["ts_code", "total_mv", "circ_mv", "turnover_rate", "pe", "pb"]],
            left_on="stock_code",
            right_on="ts_code",
            how="left",
        )

    # Winsorize 关键指标
    nodes_with_market["total_mv_win"] = winsorize_s(nodes_with_market["total_mv"])
    nodes_with_market["turnover_rate_win"] = winsorize_s(nodes_with_market["turnover_rate"])

    print("\n[Step 2] 计算规模与流动性分桶...")
    n_bins = 10  # 使用 10 分位桶以提高精细度
    
    if nodes_with_market["total_mv_win"].notna().any():
        nodes_with_market["size_bucket"] = pd.qcut(
            nodes_with_market["total_mv_win"].rank(method="first"),
            q=n_bins,
            labels=False,
            duplicates="drop"
        )
    else:
        nodes_with_market["size_bucket"] = -1

    if nodes_with_market["turnover_rate_win"].notna().any():
        nodes_with_market["liquidity_bucket"] = pd.qcut(
            nodes_with_market["turnover_rate_win"].rank(method="first"),
            q=n_bins,
            labels=False,
            duplicates="drop"
        )
    else:
        nodes_with_market["liquidity_bucket"] = -1

    print("\n[Step 3] 保存节点市场画像...")
    node_profile = nodes_with_market[["node_id", "stock_code", "total_mv", "turnover_rate", "size_bucket", "liquidity_bucket"]].copy()
    node_profile.to_parquet(baselines_cache / "node_size_liquidity_profile.parquet", index=False)
    print(f"[OK] node_size_liquidity_profile.parquet 已保存")

    # 计算随机基准
    random_same_size_ratio = 1.0 / n_bins
    random_same_liq_ratio = 1.0 / n_bins

    summary = {
        "n_bins": n_bins,
        "random_same_size_ratio": random_same_size_ratio,
        "random_same_liq_ratio": random_same_liq_ratio,
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "script": "10_size_liquidity_domain.py",
    }

    summary_path = baselines_cache / "size_liquidity_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    manifest = {
        "task_id": "T2.4",
        "task_name": "Size/Liquidity domain segmentation",
        "cache_key": cache_dir.name,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "summary": summary,
    }

    with open(manifests_dir / "t24_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T2.4 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()