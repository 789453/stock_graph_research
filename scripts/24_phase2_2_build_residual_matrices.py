#!/usr/bin/env python3
"""
T2.2.4: 构建残差矩阵 (Refactored)
根据 node_id 顺序构建残差矩阵，剥离市场、行业及风格因子。
严格遵循 Node Order Safety。
"""
import os
import json
import time
import argparse
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any
from sklearn.linear_model import LinearRegression

sys_path = str(Path(__file__).parent.parent / "src")
import sys
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from semantic_graph_research import load_config
from semantic_graph_research.phase2_graph_layers import prepare_nodes_index

def build_residual_matrices(args):
    start_time = time.time()
    
    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.2.4: 构建残差矩阵 (Refactored)")
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
    resonance_cache = phase2_cache / "resonance"
    resonance_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = phase2_cache / "manifests"

    # 1. 加载节点 (确定行顺序)
    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    nodes = prepare_nodes_index(nodes, len(nodes))
    n_nodes = len(nodes)
    print(f"[OK] 加载 {n_nodes} 节点，行序已锁定")

    # 2. 加载月度面板
    panel_path = market_behavior_cache / "node_monthly_panel_2018_2026.parquet"
    if not panel_path.exists():
        print(f"[FAIL] {panel_path} 不存在")
        sys.exit(1)
    panel = pd.read_parquet(panel_path)
    
    # 加载行业数据
    sw_member_path = Path(config["paths"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        nodes = nodes.merge(sw_member[["ts_code", "l1_name", "l3_name"]], 
                          left_on="stock_code", right_on="ts_code", how="left")
    
    # 3. 准备回归特征 (Size/Liquidity)
    # 尝试从画像表加载，如果没有则从面板计算平均值
    profile_path = phase2_cache / "baselines" / "node_size_liquidity_profile.parquet"
    if profile_path.exists():
        profile = pd.read_parquet(profile_path)
        nodes = nodes.merge(profile[["node_id", "log_total_mv", "log_amount"]], on="node_id", how="left")
    else:
        print("[WARN] 节点画像缺失，将从面板动态计算 Size/Liq 特征")
        # 从面板中每个股票的平均 amount 作为特征
        avg_features = panel.groupby("node_id")["monthly_amount"].mean().reset_index()
        avg_features["log_amount"] = np.log1p(avg_features["monthly_amount"])
        nodes = nodes.merge(avg_features[["node_id", "log_amount"]], on="node_id", how="left")
        nodes["log_total_mv"] = nodes["log_amount"] # 简化替代

    # 填充缺失值
    nodes["log_total_mv"] = nodes["log_total_mv"].fillna(nodes["log_total_mv"].median())
    nodes["log_amount"] = nodes["log_amount"].fillna(nodes["log_amount"].median())

    # 4. 构建矩阵
    months = sorted(panel["month"].unique())
    n_months = len(months)
    month_to_idx = {m: i for i, m in enumerate(months)}
    
    matrix_names = ["monthly_return", "ret_resid_market", "ret_resid_l1", "ret_resid_full"]
    matrices = {name: np.full((n_nodes, n_months), np.nan, dtype=np.float32) for name in matrix_names}
    
    print(f"Decomposing {n_months} months...")
    for m_idx, month in enumerate(months):
        m_data = panel[panel["month"] == month].copy()
        if m_data.empty: continue
        
        # 合并节点特征
        m_data = m_data.merge(nodes[["node_id", "l1_name", "log_total_mv", "log_amount"]], on="node_id", how="left")
        
        # Raw return
        matrices["monthly_return"][m_data["node_id"].values, m_idx] = m_data["monthly_return"].values
        
        # 1. Market Residual
        m_mean = m_data["monthly_return"].mean()
        m_data["resid_market"] = m_data["monthly_return"] - m_mean
        matrices["ret_resid_market"][m_data["node_id"].values, m_idx] = m_data["resid_market"].values
        
        # 2. L1 Residual
        m_data["resid_l1"] = m_data["monthly_return"] - m_data.groupby("l1_name")["monthly_return"].transform("mean")
        matrices["ret_resid_l1"][m_data["node_id"].values, m_idx] = m_data["resid_l1"].fillna(m_data["resid_market"]).values
        
        # 3. Full Residual (OLS on L1 residual)
        valid = m_data.dropna(subset=["resid_l1", "log_total_mv", "log_amount"])
        if len(valid) > 50:
            X = valid[["log_total_mv", "log_amount"]].values
            y = valid["resid_l1"].values
            reg = LinearRegression().fit(X, y)
            valid_resid = y - reg.predict(X)
            matrices["ret_resid_full"][valid["node_id"].values, m_idx] = valid_resid
            
    # 5. 保存矩阵
    for name, mat in matrices.items():
        np.save(resonance_cache / f"matrix_{name}.npy", mat)
        
    with open(resonance_cache / "matrix_metadata.json", "w") as f:
        json.dump({
            "row_order": "node_id",
            "col_order": "month",
            "months": months,
            "shape": [n_nodes, n_months],
            "node_count": n_nodes,
            "created_at": datetime.now().isoformat()
        }, f, indent=2)

    # 6. Manifest
    elapsed = time.time() - start_time
    manifest = {
        "task_id": "T2.2.4",
        "task_name": "build_residual_matrices",
        "status": "success",
        "cache_key": cache_dir.name,
        "outputs": {
            "full_residual_matrix": str(resonance_cache / "matrix_ret_resid_full.npy"),
            "metadata": str(resonance_cache / "matrix_metadata.json")
        },
        "node_order_safety": "node_id_aligned"
    }
    
    with open(manifests_dir / "t24_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Finished building {len(matrices)} matrices. Elapsed: {elapsed:.1f}s")

def main():
    parser = argparse.ArgumentParser(description="T2.2.4: 构建残差矩阵")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()
    build_residual_matrices(args)

if __name__ == "__main__":
    main()
