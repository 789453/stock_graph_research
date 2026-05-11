#!/usr/bin/env python3
"""
T2.2.6: 计算边级市场指标 (Refactored)
计算语义边和匹配随机边的月度残差相关性。
严格遵循 Node Order Safety 和 Matrix Metadata 断言。
"""
import os
import json
import time
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm

sys_path = str(Path(__file__).parent.parent / "src")
import sys
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from semantic_graph_research import load_config
from semantic_graph_research.phase2_graph_layers import prepare_nodes_index

def compute_edge_market_metrics(args):
    start_time = time.time()
    
    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.2.6: 计算边级市场指标 (Refactored)")
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
            cache_dir = sorted(cache_dirs)[-1]

    phase2_cache = cache_dir / "phase2"
    resonance_cache = phase2_cache / "resonance"
    manifests_dir = phase2_cache / "manifests"

    # 1. 加载矩阵元数据并断言
    meta_path = resonance_cache / "matrix_metadata.json"
    if not meta_path.exists():
        print(f"[FAIL] 矩阵元数据不存在: {meta_path}")
        sys.exit(1)
    with open(meta_path) as f:
        matrix_meta = json.load(f)
    
    if matrix_meta.get("row_order") != "node_id":
        print(f"[FAIL] 矩阵行序非 node_id: {matrix_meta.get('row_order')}")
        sys.exit(1)
    print(f"[OK] 矩阵元数据验证通过 (row_order=node_id)")

    # 2. 加载残差矩阵
    matrix_path = resonance_cache / "matrix_ret_resid_full.npy"
    if not matrix_path.exists():
        matrix_path = resonance_cache / "matrix_ret_resid_l1.npy" # Fallback
    
    if not matrix_path.exists():
        print(f"[FAIL] 残差矩阵不存在")
        sys.exit(1)
    
    res_matrix = np.load(matrix_path)
    print(f"[OK] 加载残差矩阵: {res_matrix.shape}")

    # 3. 加载边
    edges_path = phase2_cache / "edge_layers" / "edge_candidates_k100.parquet"
    edges = pd.read_parquet(edges_path)
    edges_k20 = edges[edges["rank"] <= 20].copy()
    
    matched_path = resonance_cache / "matched_random_edges_k20.parquet"
    if not matched_path.exists():
        print(f"[FAIL] 匹配随机边不存在: {matched_path}")
        sys.exit(1)
    matched_df = pd.read_parquet(matched_path)

    # 4. 计算相关性
    print("[Step 1] 计算边级残差相关性...")
    
    def compute_corrs(src_ids, dst_ids, matrix):
        corrs = []
        for u, v in tqdm(zip(src_ids, dst_ids), total=len(src_ids), desc="Correlating"):
            u, v = int(u), int(v)
            vec_u = matrix[u]
            vec_v = matrix[v]
            mask = np.isfinite(vec_u) & np.isfinite(vec_v)
            if mask.sum() >= 12:
                corrs.append(np.corrcoef(vec_u[mask], vec_v[mask])[0, 1])
            else:
                corrs.append(np.nan)
        return np.array(corrs)

    edges_k20["resid_corr"] = compute_corrs(edges_k20["src_node_id"].values, edges_k20["dst_node_id"].values, res_matrix)
    matched_df["resid_corr"] = compute_corrs(matched_df["src_node_id"].values, matched_df["random_dst_node_id"].values, res_matrix)

    # 5. 保存结果
    edges_k20.to_parquet(resonance_cache / "edge_resonance_metrics_k20.parquet", index=False)
    matched_df.to_parquet(resonance_cache / "matched_random_resonance_k20.parquet", index=False)
    
    # 6. 生成摘要
    summary = {
        "semantic_mean": float(edges_k20["resid_corr"].dropna().mean()),
        "random_mean": float(matched_df["resid_corr"].dropna().mean()),
        "lift": float(edges_k20["resid_corr"].dropna().mean() - matched_df["resid_corr"].dropna().mean()),
        "n_semantic": int(edges_k20["resid_corr"].notna().sum()),
        "n_random": int(matched_df["resid_corr"].notna().sum())
    }
    
    with open(resonance_cache / "resonance_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # 7. Manifest
    elapsed = time.time() - start_time
    manifest = {
        "task_id": "T2.2.6",
        "task_name": "compute_edge_market_metrics",
        "status": "success",
        "cache_key": cache_dir.name,
        "summary": summary,
        "node_order_safety": "node_id_aligned"
    }
    
    with open(manifests_dir / "t26_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"T2.2.6 完成. Lift: {summary['lift']:.4f}. Elapsed: {elapsed:.1f}s")

def main():
    parser = argparse.ArgumentParser(description="T2.2.6: 计算边级市场指标")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()
    compute_edge_market_metrics(args)

if __name__ == "__main__":
    main()
