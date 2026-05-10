#!/usr/bin/env python3
"""
T2.4: 市值/流动性分域
基于 stock_daily_basic 计算节点规模分布和流动性画像
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
    baselines_cache = phase2_cache / "baselines"
    baselines_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = project_root / "outputs" / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("T2.4: 市值/流动性分域")
    print("=" * 60)

    import pandas as pd
    import numpy as np

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    stock_codes = nodes["stock_code"].tolist()

    print("\n[Step 1] 加载 stock_daily_basic...")
    stock_daily_basic_path = Path("/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily_basic.parquet")
    if not stock_daily_basic_path.exists():
        print("[WARN] stock_daily_basic 不存在，跳过流动性计算")
        nodes_with_market = nodes.copy()
        nodes_with_market["total_market_cap"] = np.nan
        nodes_with_market["circ_market_cap"] = np.nan
        nodes_with_market["avg_turnover_1y"] = np.nan
        nodes_with_market["avg_volume_1y"] = np.nan
        nodes_with_market["size_quintile"] = np.nan
        nodes_with_market["liquidity_quintile"] = np.nan
    else:
        stock_daily_basic = pd.read_parquet(stock_daily_basic_path)
        print(f"[OK] stock_daily_basic: {len(stock_daily_basic)} rows")

        latest_data = stock_daily_basic.groupby("ts_code").apply(
            lambda x: x.sort_values("trade_date").iloc[-1],
            include_groups=False
        ).reset_index()
        print(f"[OK] 最新数据点: {len(latest_data)} stocks")

        nodes_with_market = nodes.merge(
            latest_data[["ts_code", "total_mv", "circ_mv", "turnover_rate"]],
            left_on="stock_code",
            right_on="ts_code",
            how="left",
        )

        last_1y_date_str = latest_data["trade_date"].max()
        last_1y_date = pd.to_datetime(last_1y_date_str, format="%Y%m%d")
        last_1y_threshold = (last_1y_date - pd.DateOffset(years=1)).strftime("%Y%m%d")
        last_1y = stock_daily_basic[stock_daily_basic["trade_date"] >= last_1y_threshold]
        if len(last_1y) > 0:
            avg_1y = last_1y.groupby("ts_code").agg(
                avg_turnover_rate=("turnover_rate", "mean"),
            ).reset_index()
            nodes_with_market = nodes_with_market.merge(
                avg_1y,
                on="ts_code",
                how="left",
            )
            nodes_with_market["avg_turnover_1y"] = nodes_with_market["avg_turnover_rate"]
        else:
            nodes_with_market["avg_turnover_1y"] = np.nan

        print("\n[Step 2] 计算规模五分位...")
        cap_col = "total_mv"
        if cap_col in nodes_with_market.columns and nodes_with_market[cap_col].notna().sum() > 0:
            nodes_with_market["size_quintile"] = pd.qcut(
                nodes_with_market[cap_col].rank(method="first"),
                q=5,
                labels=[1, 2, 3, 4, 5],
                duplicates="drop"
            )
            size_dist = nodes_with_market["size_quintile"].value_counts().sort_index()
            print(f"规模五分位分布:")
            print(size_dist)
        else:
            nodes_with_market["size_quintile"] = np.nan

        print("\n[Step 3] 计算流动性五分位...")
        liq_col = "avg_turnover_1y"
        if liq_col in nodes_with_market.columns and nodes_with_market[liq_col].notna().sum() > 0:
            nodes_with_market["liquidity_quintile"] = pd.qcut(
                nodes_with_market[liq_col].rank(method="first"),
                q=5,
                labels=[1, 2, 3, 4, 5],
                duplicates="drop"
            )
            liq_dist = nodes_with_market["liquidity_quintile"].value_counts().sort_index()
            print(f"流动性五分位分布:")
            print(liq_dist)
        else:
            nodes_with_market["liquidity_quintile"] = np.nan

    print("\n[Step 4] 保存节点市场画像...")
    profile_cols = ["node_id", "stock_code", "stock_name", "total_mv", "circ_mv",
                    "avg_turnover_1y", "size_quintile", "liquidity_quintile"]
    existing_cols = [c for c in profile_cols if c in nodes_with_market.columns]
    node_profile = nodes_with_market[existing_cols].copy()
    node_profile.to_parquet(baselines_cache / "node_size_liquidity_profile.parquet", index=False)
    print(f"[OK] node_size_liquidity_profile.parquet 已保存: {len(node_profile)} nodes")

    print("\n[Step 5] 生成规模-流动性交叉统计...")
    if "size_quintile" in node_profile.columns and "liquidity_quintile" in node_profile.columns:
        cross_tab = pd.crosstab(
            node_profile["size_quintile"].dropna(),
            node_profile["liquidity_quintile"].dropna(),
            margins=True
        )
        print(cross_tab)

        cross_tab_path = output_dir / "size_liquidity_cross_tab.md"
        with open(cross_tab_path, "w", encoding="utf-8") as f:
            f.write("# Size × Liquidity Cross Tabulation\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(cross_tab.to_string() + "\n\n")
        print(f"[OK] 交叉表已保存: {cross_tab_path}")

    print("\n[Step 6] 计算市值统计...")
    cap_stats = {}
    cap_col = "total_market_cap"
    if cap_col in nodes_with_market.columns:
        valid = nodes_with_market[cap_col].dropna()
        if len(valid) > 0:
            cap_stats = {
                "count": int(len(valid)),
                "mean": float(np.mean(valid)),
                "median": float(np.median(valid)),
                "std": float(np.std(valid)),
                "min": float(np.min(valid)),
                "max": float(np.max(valid)),
                "q25": float(np.percentile(valid, 25)),
                "q75": float(np.percentile(valid, 75)),
            }
            print(json.dumps(cap_stats, indent=2))

    summary = {
        "total_nodes": len(nodes),
        "nodes_with_market_data": int(nodes_with_market[cap_col].notna().sum()) if cap_col in nodes_with_market.columns else 0,
        "cap_stats": cap_stats,
        "size_quintile_dist": {int(k): int(v) for k, v in nodes_with_market["size_quintile"].value_counts().sort_index().items()} if "size_quintile" in nodes_with_market.columns else {},
        "liquidity_quintile_dist": {int(k): int(v) for k, v in nodes_with_market["liquidity_quintile"].value_counts().sort_index().items()} if "liquidity_quintile" in nodes_with_market.columns else {},
    }

    summary_path = baselines_cache / "size_liquidity_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] size_liquidity_summary.json 已保存")

    manifest = {
        "task_id": "T2.4",
        "task_name": "Size/Liquidity domain segmentation",
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "inputs": [str(stock_daily_basic_path)] if stock_daily_basic_path.exists() else [],
        "outputs": [
            str(baselines_cache / "node_size_liquidity_profile.parquet"),
            str(summary_path),
        ],
        "parameters": {},
        "warnings": [],
        "error": None,
    }

    with open(manifests_dir / "t24_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.4 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()