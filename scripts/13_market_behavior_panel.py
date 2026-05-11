#!/usr/bin/env python3
"""
T2.7: 2018-2026 市场行为月度面板 (Refactored)
构建月度面板，支持残差矩阵生成和 H5 检验。
严格遵循 Node Order Safety 和 Phase 2.3 规范。
"""
import sys
import json
import argparse
import pandas as pd
import numpy as np
import duckdb
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.phase2_graph_layers import prepare_nodes_index

def main():
    parser = argparse.ArgumentParser(description="T2.7: 2018-2026 市场行为月度面板")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.7: 2018-2026 市场行为月度面板 (Refactored)")
    print(f"Config: {args.config}")
    print("=" * 60)

    cache_root = Path("cache") / "semantic_graph"
    if args.cache_key:
        cache_dir = cache_root / args.cache_key
    else:
        # 尝试从 config 中获取
        cache_dir_str = config.get("paths", {}).get("semantic_graph_cache")
        if cache_dir_str:
            cache_dir = Path(cache_dir_str)
        else:
            cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
            if not cache_dirs:
                print("[FAIL] 未找到缓存")
                sys.exit(1)
            cache_dir = sorted(cache_dirs)[-1]

    phase2_cache = cache_dir / "phase2"
    market_behavior_cache = phase2_cache / "market_behavior"
    market_behavior_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = phase2_cache / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    # 1. 加载节点
    nodes_path = cache_dir / "nodes.parquet"
    if not nodes_path.exists():
        print(f"[FAIL] {nodes_path} 不存在")
        sys.exit(1)
        
    nodes = pd.read_parquet(nodes_path)
    nodes = prepare_nodes_index(nodes, len(nodes))
    stock_codes = nodes["stock_code"].tolist()
    print(f"[OK] 加载 {len(nodes)} 节点")

    # 2. 查询行情数据 (使用 DuckDB 加速)
    daily_path = config["paths"]["stock_daily_path"]
    print(f"[Step 1] 从 {daily_path} 加载数据...")
    
    # 限制时间范围和股票范围
    query = f"""
    SELECT ts_code, trade_date, close, pct_chg, amount
    FROM read_parquet('{daily_path}')
    WHERE trade_date BETWEEN '20180101' AND '20261231'
    AND ts_code IN {tuple(stock_codes)}
    """
    daily = duckdb.query(query).df()
    print(f"[OK] 查询到 {len(daily)} 条记录")

    # 3. 处理月度指标
    print("[Step 2] 计算月度指标...")
    daily["month"] = daily["trade_date"].str[:6]
    
    def compute_monthly_stats(group):
        group = group.sort_values("trade_date")
        prices = group["close"].values
        pct_chgs = group["pct_chg"].values
        
        # 月度收益: 期末/期初 - 1 (注意：由于是日频数据，简化为期末收盘价相对于期初收盘价的变化，更严谨应包含 pre_close)
        # 这里为了稳健，直接使用 pct_chg 的累计乘积
        monthly_return = (1 + pct_chgs / 100.0).prod() - 1
        
        # 日对数收益率的波动率
        log_rets = np.log(1 + pct_chgs / 100.0)
        volatility = np.std(log_rets) if len(log_rets) > 0 else 0.0
        
        # 最大回撤
        mdd = (1 - prices / np.maximum.accumulate(prices)).max() if len(prices) > 0 else 0.0
        
        return pd.Series({
            "monthly_return": monthly_return,
            "monthly_amount": group["amount"].sum(),
            "monthly_volatility": volatility,
            "max_drawdown": mdd,
            "trading_days": len(group)
        })

    # 计算月度指标
    monthly_panel = daily.groupby(["ts_code", "month"]).apply(compute_monthly_stats, include_groups=False).reset_index()
    
    # 4. 强制对齐 node_id (Node Order Safety)
    print("[Step 3] 强制对齐 node_id 与月份矩阵...")
    monthly_panel = monthly_panel.merge(nodes[["node_id", "stock_code"]], left_on="ts_code", right_on="stock_code", how="inner")
    
    # 生成月份列表并排序
    all_months = sorted(monthly_panel["month"].unique())
    month_to_idx = {m: i for i, m in enumerate(all_months)}
    monthly_panel["month_idx"] = monthly_panel["month"].map(month_to_idx)
    
    print(f"[OK] 面板涵盖 {len(all_months)} 个月份: {all_months[0]} - {all_months[-1]}")

    # 5. 保存月度面板
    print("[Step 4] 保存结果...")
    monthly_panel.to_parquet(market_behavior_cache / "node_monthly_panel_2018_2026.parquet", index=False)
    
    # 同时保留一个年度摘要版供 legacy 兼容
    monthly_panel["year"] = monthly_panel["month"].str[:4]
    annual_panel = monthly_panel.groupby(["node_id", "stock_code", "year"]).agg(
        annual_return=("monthly_return", lambda x: (1 + x).prod() - 1),
        avg_volatility=("monthly_volatility", "mean"),
        total_amount=("monthly_amount", "sum"),
        total_trading_days=("trading_days", "sum")
    ).reset_index()
    annual_panel.to_parquet(market_behavior_cache / "node_annual_panel_2018_2026.parquet", index=False)

    # 6. 生成摘要与 Manifest
    summary = {
        "total_nodes": len(nodes),
        "total_months": len(all_months),
        "panel_records": len(monthly_panel),
        "month_range": [all_months[0], all_months[-1]],
        "avg_trading_days_per_month": float(monthly_panel["trading_days"].mean())
    }
    
    with open(market_behavior_cache / "market_behavior_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    manifest = {
        "task_id": "T2.7",
        "task_name": "Monthly market behavior panel",
        "cache_key": cache_dir.name,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "outputs": {
            "monthly_panel": str(market_behavior_cache / "node_monthly_panel_2018_2026.parquet"),
            "annual_panel": str(market_behavior_cache / "node_annual_panel_2018_2026.parquet")
        },
        "node_order_policy": "node_id_aligned"
    }

    with open(manifests_dir / "t27_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T2.7 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
